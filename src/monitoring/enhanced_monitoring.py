"""Enhanced monitoring and observability features for the ajentik system."""

import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager
import json

import logfire
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.chart import BarChart
from rich import box

from ..models.schemas import AgentMetrics
from ..utils.logfire_setup import LogfireContextManager


console = Console()


class MetricsCollector:
    """Collects and aggregates metrics for real-time monitoring."""
    
    def __init__(self):
        self.metrics: Dict[str, AgentMetrics] = defaultdict(lambda: AgentMetrics())
        self.tool_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "usage_count": 0,
            "success_count": 0,
            "total_time": 0.0,
            "errors": []
        })
        self.model_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "requests": 0,
            "tokens": 0,
            "cost": 0.0,
            "latencies": []
        })
        self.error_log: List[Dict[str, Any]] = []
        self.start_time = time.time()
    
    def record_agent_request(self, agent_name: str, success: bool, response_time: float, tokens: int = 0, cost: float = 0.0):
        """Record an agent request."""
        metrics = self.metrics[agent_name]
        metrics.total_requests += 1
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
        
        # Update average response time
        total_time = metrics.average_response_time * (metrics.total_requests - 1) + response_time
        metrics.average_response_time = total_time / metrics.total_requests
        
        metrics.total_tokens_used += tokens
        metrics.total_cost += cost
        
        # Log to Logfire
        logfire.info(
            "Agent request recorded",
            agent=agent_name,
            success=success,
            response_time_ms=response_time * 1000,
            tokens=tokens,
            cost=cost
        )
    
    def record_tool_usage(self, tool_name: str, agent_name: str, success: bool, execution_time: float, error: Optional[str] = None):
        """Record tool usage."""
        metrics = self.tool_metrics[tool_name]
        metrics["usage_count"] += 1
        if success:
            metrics["success_count"] += 1
        metrics["total_time"] += execution_time
        
        if error:
            metrics["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent_name,
                "error": error
            })
        
        # Log to Logfire
        logfire.info(
            "Tool usage recorded",
            tool=tool_name,
            agent=agent_name,
            success=success,
            execution_time_ms=execution_time * 1000,
            error=error
        )
    
    def record_model_usage(self, model: str, tokens: int, latency: float, cost: float):
        """Record model usage metrics."""
        metrics = self.model_metrics[model]
        metrics["requests"] += 1
        metrics["tokens"] += tokens
        metrics["cost"] += cost
        metrics["latencies"].append(latency)
        
        # Keep only last 100 latencies
        if len(metrics["latencies"]) > 100:
            metrics["latencies"] = metrics["latencies"][-100:]
        
        # Log to Logfire
        logfire.info(
            "Model usage recorded",
            model=model,
            tokens=tokens,
            latency_ms=latency * 1000,
            cost=cost
        )
    
    def record_error(self, component: str, error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        """Record an error."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        self.error_log.append(error_entry)
        
        # Keep only last 100 errors
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-100:]
        
        # Log to Logfire
        logfire.error(
            "Error recorded",
            component=component,
            error_type=error_type,
            error_message=error_message,
            **context or {}
        )
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        total_requests = sum(m.total_requests for m in self.metrics.values())
        total_successes = sum(m.successful_requests for m in self.metrics.values())
        success_rate = (total_successes / total_requests * 100) if total_requests > 0 else 0
        
        uptime = time.time() - self.start_time
        recent_errors = len([e for e in self.error_log if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(minutes=5)])
        
        return {
            "status": "healthy" if success_rate > 95 and recent_errors < 5 else "degraded" if success_rate > 80 else "unhealthy",
            "uptime_seconds": uptime,
            "total_requests": total_requests,
            "success_rate": success_rate,
            "recent_errors": recent_errors,
            "active_agents": len(self.metrics),
            "total_cost": sum(m.total_cost for m in self.metrics.values()),
            "total_tokens": sum(m.total_tokens_used for m in self.metrics.values())
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


@contextmanager
def monitor_operation(operation_name: str, agent_name: Optional[str] = None, **tags):
    """Context manager for monitoring operations with automatic metrics collection."""
    start_time = time.time()
    success = True
    error_info = None
    
    with LogfireContextManager(operation_name, agent=agent_name, **tags) as span:
        try:
            yield span
        except Exception as e:
            success = False
            error_info = {
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
            metrics_collector.record_error(
                component=agent_name or "system",
                error_type=type(e).__name__,
                error_message=str(e),
                context={"operation": operation_name, **tags}
            )
            raise
        finally:
            duration = time.time() - start_time
            if agent_name:
                metrics_collector.record_agent_request(
                    agent_name=agent_name,
                    success=success,
                    response_time=duration
                )
            
            # Log operation completion
            logfire.info(
                f"Operation {operation_name} completed",
                success=success,
                duration_ms=duration * 1000,
                agent=agent_name,
                **tags,
                **(error_info or {})
            )


def create_monitoring_dashboard() -> Layout:
    """Create a real-time monitoring dashboard."""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    layout["main"].split_row(
        Layout(name="agents", ratio=1),
        Layout(name="tools", ratio=1),
        Layout(name="health", ratio=1)
    )
    
    # Header
    health = metrics_collector.get_system_health()
    status_color = {
        "healthy": "green",
        "degraded": "yellow", 
        "unhealthy": "red"
    }.get(health["status"], "white")
    
    layout["header"].update(
        Panel(
            f"[bold]System Monitoring Dashboard[/bold]\n"
            f"Status: [{status_color}]{health['status'].upper()}[/{status_color}] | "
            f"Uptime: {health['uptime_seconds']:.0f}s | "
            f"Success Rate: {health['success_rate']:.1f}%",
            style="bold blue"
        )
    )
    
    # Agent metrics
    agent_table = Table(title="Agent Performance", box=box.ROUNDED)
    agent_table.add_column("Agent", style="cyan")
    agent_table.add_column("Requests", justify="right")
    agent_table.add_column("Success Rate", justify="right")
    agent_table.add_column("Avg Time", justify="right")
    
    for agent_name, metrics in metrics_collector.metrics.items():
        agent_table.add_row(
            agent_name,
            str(metrics.total_requests),
            f"{metrics.success_rate:.1f}%",
            f"{metrics.average_response_time:.2f}s"
        )
    
    layout["agents"].update(Panel(agent_table, border_style="green"))
    
    # Tool metrics
    tool_table = Table(title="Tool Usage", box=box.ROUNDED)
    tool_table.add_column("Tool", style="cyan")
    tool_table.add_column("Usage", justify="right")
    tool_table.add_column("Success", justify="right")
    tool_table.add_column("Avg Time", justify="right")
    
    for tool_name, metrics in metrics_collector.tool_metrics.items():
        success_rate = (metrics["success_count"] / metrics["usage_count"] * 100) if metrics["usage_count"] > 0 else 0
        avg_time = (metrics["total_time"] / metrics["usage_count"]) if metrics["usage_count"] > 0 else 0
        
        tool_table.add_row(
            tool_name,
            str(metrics["usage_count"]),
            f"{success_rate:.1f}%",
            f"{avg_time:.2f}s"
        )
    
    layout["tools"].update(Panel(tool_table, border_style="yellow"))
    
    # Health metrics
    health_table = Table(title="System Health", box=box.ROUNDED)
    health_table.add_column("Metric", style="cyan")
    health_table.add_column("Value", justify="right")
    
    health_table.add_row("Total Requests", str(health["total_requests"]))
    health_table.add_row("Active Agents", str(health["active_agents"]))
    health_table.add_row("Recent Errors", str(health["recent_errors"]))
    health_table.add_row("Total Tokens", f"{health['total_tokens']:,}")
    health_table.add_row("Total Cost", f"${health['total_cost']:.2f}")
    
    layout["health"].update(Panel(health_table, border_style="blue"))
    
    # Footer
    layout["footer"].update(
        Panel(
            f"[dim]Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
            style="dim"
        )
    )
    
    return layout


async def live_monitoring_dashboard(refresh_rate: float = 1.0):
    """Display a live monitoring dashboard that updates in real-time."""
    with Live(create_monitoring_dashboard(), refresh_per_second=1/refresh_rate, console=console) as live:
        try:
            while True:
                await asyncio.sleep(refresh_rate)
                live.update(create_monitoring_dashboard())
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped.[/yellow]")


def export_metrics(format: str = "json") -> str:
    """Export collected metrics in various formats."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "system_health": metrics_collector.get_system_health(),
        "agent_metrics": {name: metrics.dict() for name, metrics in metrics_collector.metrics.items()},
        "tool_metrics": dict(metrics_collector.tool_metrics),
        "model_metrics": dict(metrics_collector.model_metrics),
        "recent_errors": metrics_collector.error_log[-20:]  # Last 20 errors
    }
    
    if format == "json":
        return json.dumps(data, indent=2, default=str)
    elif format == "markdown":
        # Create markdown report
        md_lines = [
            "# System Metrics Report",
            f"\nGenerated: {data['timestamp']}",
            "\n## System Health",
            f"- Status: {data['system_health']['status']}",
            f"- Success Rate: {data['system_health']['success_rate']:.1f}%",
            f"- Total Requests: {data['system_health']['total_requests']}",
            "\n## Agent Performance",
        ]
        
        for agent, metrics in data['agent_metrics'].items():
            md_lines.append(f"\n### {agent}")
            md_lines.append(f"- Requests: {metrics['total_requests']}")
            md_lines.append(f"- Success Rate: {metrics['success_rate']:.1f}%")
            md_lines.append(f"- Avg Response Time: {metrics['average_response_time']:.2f}s")
        
        return "\n".join(md_lines)
    else:
        raise ValueError(f"Unsupported format: {format}")


class AlertManager:
    """Manages alerts based on metric thresholds."""
    
    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
        self.thresholds = {
            "error_rate": 10.0,  # Alert if error rate > 10%
            "response_time": 5.0,  # Alert if avg response time > 5s
            "failure_count": 10,  # Alert if failures > 10 in 5 minutes
        }
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions and return active alerts."""
        active_alerts = []
        
        # Check system health
        health = metrics_collector.get_system_health()
        if health["success_rate"] < 90:
            active_alerts.append({
                "severity": "high",
                "type": "success_rate",
                "message": f"System success rate is low: {health['success_rate']:.1f}%",
                "timestamp": datetime.now().isoformat()
            })
        
        # Check agent performance
        for agent_name, metrics in metrics_collector.metrics.items():
            if metrics.average_response_time > self.thresholds["response_time"]:
                active_alerts.append({
                    "severity": "medium",
                    "type": "response_time",
                    "message": f"Agent {agent_name} response time is high: {metrics.average_response_time:.2f}s",
                    "timestamp": datetime.now().isoformat()
                })
            
            if metrics.failed_requests > self.thresholds["failure_count"]:
                active_alerts.append({
                    "severity": "high",
                    "type": "failure_count",
                    "message": f"Agent {agent_name} has {metrics.failed_requests} failures",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Check recent errors
        recent_errors = len([e for e in metrics_collector.error_log 
                           if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(minutes=5)])
        if recent_errors > 20:
            active_alerts.append({
                "severity": "high",
                "type": "error_spike",
                "message": f"Error spike detected: {recent_errors} errors in last 5 minutes",
                "timestamp": datetime.now().isoformat()
            })
        
        return active_alerts
    
    def send_alert(self, alert: Dict[str, Any]):
        """Send an alert (log it for now, could integrate with external services)."""
        severity_emoji = {
            "high": "🚨",
            "medium": "⚠️",
            "low": "ℹ️"
        }.get(alert["severity"], "📢")
        
        logfire.warning(
            f"{severity_emoji} Alert: {alert['message']}",
            severity=alert["severity"],
            alert_type=alert["type"]
        )
        
        console.print(f"\n{severity_emoji} [bold {alert['severity']}]ALERT:[/bold {alert['severity']}] {alert['message']}")


# Global alert manager
alert_manager = AlertManager()


def start_alert_monitoring(check_interval: float = 30.0):
    """Start background alert monitoring."""
    async def monitor_alerts():
        while True:
            alerts = alert_manager.check_alerts()
            for alert in alerts:
                alert_manager.send_alert(alert)
            await asyncio.sleep(check_interval)
    
    # Run in background
    asyncio.create_task(monitor_alerts())