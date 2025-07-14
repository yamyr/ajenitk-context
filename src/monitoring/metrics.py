"""Metrics collection for monitoring."""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
from threading import Lock

from ..utils.logging import get_logger
from ..config.settings import get_settings

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class Metric:
    """Base class for metrics."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: Dict[str, List[MetricValue]] = defaultdict(list)
        self._lock = Lock()
    
    def _make_key(self, labels: Optional[Dict[str, str]] = None) -> str:
        """Create key from labels."""
        if not labels:
            return ""
        
        # Sort labels for consistent keys
        items = sorted((k, v) for k, v in labels.items() if k in self.label_names)
        return ",".join(f"{k}={v}" for k, v in items)
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current value."""
        with self._lock:
            key = self._make_key(labels)
            values = self._values.get(key, [])
            return values[-1].value if values else None
    
    def get_values(self, labels: Optional[Dict[str, str]] = None, 
                  since: Optional[float] = None) -> List[MetricValue]:
        """Get all values since timestamp."""
        with self._lock:
            key = self._make_key(labels)
            values = self._values.get(key, [])
            
            if since:
                values = [v for v in values if v.timestamp >= since]
            
            return values.copy()


class Counter(Metric):
    """Counter metric that only increases."""
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment counter."""
        if value < 0:
            raise ValueError("Counter can only increase")
        
        with self._lock:
            key = self._make_key(labels)
            current = self.get_value(labels) or 0.0
            self._values[key].append(MetricValue(current + value, labels=labels or {}))
    
    def reset(self, labels: Optional[Dict[str, str]] = None):
        """Reset counter to zero."""
        with self._lock:
            key = self._make_key(labels)
            self._values[key] = [MetricValue(0.0, labels=labels or {})]


class Gauge(Metric):
    """Gauge metric that can go up or down."""
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set gauge value."""
        with self._lock:
            key = self._make_key(labels)
            self._values[key].append(MetricValue(value, labels=labels or {}))
    
    def inc(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment gauge."""
        with self._lock:
            current = self.get_value(labels) or 0.0
            self.set(current + value, labels)
    
    def dec(self, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Decrement gauge."""
        self.inc(-value, labels)


class Histogram(Metric):
    """Histogram metric for distributions."""
    
    def __init__(self, name: str, description: str = "", 
                 labels: Optional[List[str]] = None,
                 buckets: Optional[List[float]] = None):
        super().__init__(name, description, labels)
        self.buckets = buckets or [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
        self._observations: Dict[str, List[float]] = defaultdict(list)
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Record an observation."""
        with self._lock:
            key = self._make_key(labels)
            self._observations[key].append(value)
            self._values[key].append(MetricValue(value, labels=labels or {}))
    
    def get_statistics(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        with self._lock:
            key = self._make_key(labels)
            observations = self._observations.get(key, [])
            
            if not observations:
                return {}
            
            sorted_obs = sorted(observations)
            count = len(observations)
            
            return {
                "count": count,
                "sum": sum(observations),
                "min": sorted_obs[0],
                "max": sorted_obs[-1],
                "mean": sum(observations) / count,
                "p50": sorted_obs[int(count * 0.5)],
                "p90": sorted_obs[int(count * 0.9)],
                "p99": sorted_obs[int(count * 0.99)] if count > 100 else sorted_obs[-1],
            }


class MetricsCollector:
    """Central metrics collector."""
    
    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = Lock()
        self._exporters: List[Callable] = []
        
        # Create default metrics
        self._setup_default_metrics()
    
    def _setup_default_metrics(self):
        """Setup default system metrics."""
        # Tool metrics
        self.counter("tool_executions_total", "Total tool executions", ["tool", "status"])
        self.histogram("tool_execution_duration", "Tool execution duration", ["tool"])
        self.gauge("tools_registered", "Number of registered tools")
        
        # MCP metrics
        self.counter("mcp_requests_total", "Total MCP requests", ["method", "status"])
        self.histogram("mcp_request_duration", "MCP request duration", ["method"])
        self.gauge("mcp_connections", "Active MCP connections")
        
        # System metrics
        self.gauge("memory_usage_bytes", "Memory usage in bytes")
        self.gauge("cpu_usage_percent", "CPU usage percentage")
    
    def counter(self, name: str, description: str = "", 
               labels: Optional[List[str]] = None) -> Counter:
        """Create or get counter metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name, description, labels)
            return self._metrics[name]
    
    def gauge(self, name: str, description: str = "", 
             labels: Optional[List[str]] = None) -> Gauge:
        """Create or get gauge metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name, description, labels)
            return self._metrics[name]
    
    def histogram(self, name: str, description: str = "", 
                 labels: Optional[List[str]] = None,
                 buckets: Optional[List[float]] = None) -> Histogram:
        """Create or get histogram metric."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Histogram(name, description, labels, buckets)
            return self._metrics[name]
    
    def collect_system_metrics(self):
        """Collect system metrics."""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.gauge("memory_usage_bytes").set(memory.used)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.gauge("cpu_usage_percent").set(cpu_percent)
            
        except ImportError:
            logger.debug("psutil not installed, skipping system metrics")
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics as dictionary."""
        with self._lock:
            metrics = {}
            
            for name, metric in self._metrics.items():
                metric_data = {
                    "name": name,
                    "description": metric.description,
                    "type": metric.__class__.__name__.lower(),
                    "values": {}
                }
                
                # Get all label combinations
                for key in metric._values:
                    values = metric.get_values()
                    if values:
                        metric_data["values"][key] = {
                            "current": values[-1].value,
                            "timestamp": values[-1].timestamp
                        }
                        
                        # Add histogram statistics
                        if isinstance(metric, Histogram):
                            stats = metric.get_statistics()
                            metric_data["values"][key].update(stats)
                
                metrics[name] = metric_data
            
            return metrics
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            for name, metric in self._metrics.items():
                # Add help text
                if metric.description:
                    lines.append(f"# HELP {name} {metric.description}")
                
                # Add type
                metric_type = metric.__class__.__name__.lower()
                lines.append(f"# TYPE {name} {metric_type}")
                
                # Add values
                for key, values in metric._values.items():
                    if values:
                        label_str = f"{{{key}}}" if key else ""
                        lines.append(f"{name}{label_str} {values[-1].value}")
                
                lines.append("")  # Empty line between metrics
        
        return "\n".join(lines)
    
    def save_metrics(self, path: Path):
        """Save metrics to file."""
        metrics = self.export_metrics()
        metrics["exported_at"] = datetime.utcnow().isoformat()
        
        with open(path, "w") as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Saved metrics to {path}")
    
    def add_exporter(self, exporter: Callable):
        """Add custom exporter function."""
        self._exporters.append(exporter)
    
    def run_exporters(self):
        """Run all registered exporters."""
        metrics = self.export_metrics()
        
        for exporter in self._exporters:
            try:
                exporter(metrics)
            except Exception as e:
                logger.error(f"Exporter failed: {e}")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector