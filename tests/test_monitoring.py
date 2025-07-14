"""Tests for monitoring and observability features."""

import asyncio
import json
import time
from unittest.mock import patch, MagicMock, call

import pytest

from src.monitoring import (
    MetricsCollector,
    monitor_operation,
    create_monitoring_dashboard,
    export_metrics,
    AlertManager,
    metrics_collector,
    alert_manager
)
from src.monitoring.enhanced_monitoring import start_alert_monitoring


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def test_record_agent_request_success(self):
        """Test recording successful agent request."""
        collector = MetricsCollector()
        
        collector.record_agent_request(
            agent_name="TestAgent",
            success=True,
            response_time=1.5,
            tokens=100,
            cost=0.05
        )
        
        metrics = collector.metrics["TestAgent"]
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.average_response_time == 1.5
        assert metrics.total_tokens_used == 100
        assert metrics.total_cost == 0.05
        assert metrics.success_rate == 100.0
    
    def test_record_agent_request_failure(self):
        """Test recording failed agent request."""
        collector = MetricsCollector()
        
        collector.record_agent_request(
            agent_name="TestAgent",
            success=False,
            response_time=0.5
        )
        
        metrics = collector.metrics["TestAgent"]
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1
        assert metrics.success_rate == 0.0
    
    def test_record_multiple_requests(self):
        """Test recording multiple requests updates averages correctly."""
        collector = MetricsCollector()
        
        # Record 3 requests with different response times
        collector.record_agent_request("TestAgent", True, 1.0)
        collector.record_agent_request("TestAgent", True, 2.0)
        collector.record_agent_request("TestAgent", False, 3.0)
        
        metrics = collector.metrics["TestAgent"]
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 2
        assert metrics.failed_requests == 1
        assert metrics.average_response_time == 2.0  # (1+2+3)/3
        assert metrics.success_rate == pytest.approx(66.67, rel=0.01)
    
    def test_record_tool_usage(self):
        """Test recording tool usage."""
        collector = MetricsCollector()
        
        collector.record_tool_usage(
            tool_name="file_reader",
            agent_name="TestAgent",
            success=True,
            execution_time=0.25
        )
        
        tool_metrics = collector.tool_metrics["file_reader"]
        assert tool_metrics["usage_count"] == 1
        assert tool_metrics["success_count"] == 1
        assert tool_metrics["total_time"] == 0.25
        assert len(tool_metrics["errors"]) == 0
    
    def test_record_tool_usage_with_error(self):
        """Test recording tool usage with error."""
        collector = MetricsCollector()
        
        collector.record_tool_usage(
            tool_name="web_search",
            agent_name="TestAgent",
            success=False,
            execution_time=1.0,
            error="Connection timeout"
        )
        
        tool_metrics = collector.tool_metrics["web_search"]
        assert tool_metrics["usage_count"] == 1
        assert tool_metrics["success_count"] == 0
        assert len(tool_metrics["errors"]) == 1
        assert tool_metrics["errors"][0]["error"] == "Connection timeout"
    
    def test_record_model_usage(self):
        """Test recording model usage."""
        collector = MetricsCollector()
        
        collector.record_model_usage(
            model="gpt-4",
            tokens=500,
            latency=2.0,
            cost=0.10
        )
        
        model_metrics = collector.model_metrics["gpt-4"]
        assert model_metrics["requests"] == 1
        assert model_metrics["tokens"] == 500
        assert model_metrics["cost"] == 0.10
        assert len(model_metrics["latencies"]) == 1
        assert model_metrics["latencies"][0] == 2.0
    
    def test_record_error(self):
        """Test recording errors."""
        collector = MetricsCollector()
        
        collector.record_error(
            component="TestAgent",
            error_type="ValueError",
            error_message="Invalid input",
            context={"input": "test"}
        )
        
        assert len(collector.error_log) == 1
        error = collector.error_log[0]
        assert error["component"] == "TestAgent"
        assert error["error_type"] == "ValueError"
        assert error["error_message"] == "Invalid input"
        assert error["context"]["input"] == "test"
    
    def test_error_log_limit(self):
        """Test that error log is limited to 100 entries."""
        collector = MetricsCollector()
        
        # Add 150 errors
        for i in range(150):
            collector.record_error(
                component="Test",
                error_type="TestError",
                error_message=f"Error {i}"
            )
        
        assert len(collector.error_log) == 100
        # Should keep the most recent errors
        assert collector.error_log[-1]["error_message"] == "Error 149"
    
    def test_get_system_health(self):
        """Test system health calculation."""
        collector = MetricsCollector()
        
        # Record some metrics
        collector.record_agent_request("Agent1", True, 1.0, 100, 0.05)
        collector.record_agent_request("Agent1", True, 1.0, 100, 0.05)
        collector.record_agent_request("Agent2", False, 2.0)
        
        health = collector.get_system_health()
        
        assert health["total_requests"] == 3
        assert health["success_rate"] == pytest.approx(66.67, rel=0.01)
        assert health["active_agents"] == 2
        assert health["total_cost"] == 0.10
        assert health["total_tokens"] == 200
        assert health["status"] == "degraded"  # Due to < 95% success rate


class TestMonitorOperation:
    """Test monitor_operation context manager."""
    
    @patch('src.monitoring.enhanced_monitoring.logfire')
    def test_monitor_operation_success(self, mock_logfire):
        """Test successful operation monitoring."""
        with monitor_operation("test_op", agent_name="TestAgent", custom_tag="value"):
            time.sleep(0.1)  # Simulate some work
        
        # Should log the operation completion
        mock_logfire.info.assert_called()
        call_args = mock_logfire.info.call_args
        assert "Operation test_op completed" in call_args[0][0]
        assert call_args[1]["success"] is True
        assert call_args[1]["agent"] == "TestAgent"
        assert "duration_ms" in call_args[1]
    
    @patch('src.monitoring.enhanced_monitoring.logfire')
    def test_monitor_operation_failure(self, mock_logfire):
        """Test operation monitoring with failure."""
        with pytest.raises(ValueError):
            with monitor_operation("test_op", agent_name="TestAgent"):
                raise ValueError("Test error")
        
        # Should record the error
        mock_logfire.info.assert_called()
        call_args = mock_logfire.info.call_args
        assert call_args[1]["success"] is False
        assert "error_type" in call_args[1]
        assert call_args[1]["error_type"] == "ValueError"
    
    def test_monitor_operation_updates_metrics(self):
        """Test that monitor_operation updates global metrics."""
        # Reset metrics
        metrics_collector.metrics.clear()
        
        with monitor_operation("test_op", agent_name="TestAgent"):
            pass
        
        assert "TestAgent" in metrics_collector.metrics
        assert metrics_collector.metrics["TestAgent"].total_requests == 1
        assert metrics_collector.metrics["TestAgent"].successful_requests == 1


class TestDashboardCreation:
    """Test dashboard creation functionality."""
    
    def test_create_monitoring_dashboard(self):
        """Test creating monitoring dashboard layout."""
        # Add some test data
        metrics_collector.record_agent_request("ChatAgent", True, 1.0, 100, 0.05)
        metrics_collector.record_tool_usage("file_reader", "ChatAgent", True, 0.5)
        
        dashboard = create_monitoring_dashboard()
        
        # Dashboard should be a Layout object
        assert hasattr(dashboard, 'split_column')
        
        # Convert to string to check content
        dashboard_str = str(dashboard)
        assert "System Monitoring Dashboard" in dashboard_str
        assert "Agent Performance" in dashboard_str
        assert "Tool Usage" in dashboard_str
        assert "System Health" in dashboard_str


class TestMetricsExport:
    """Test metrics export functionality."""
    
    def test_export_metrics_json(self):
        """Test exporting metrics as JSON."""
        # Add test data
        metrics_collector.record_agent_request("TestAgent", True, 1.0, 100, 0.05)
        metrics_collector.record_error("TestAgent", "TestError", "Test message")
        
        json_export = export_metrics("json")
        data = json.loads(json_export)
        
        assert "timestamp" in data
        assert "system_health" in data
        assert "agent_metrics" in data
        assert "TestAgent" in data["agent_metrics"]
        assert data["agent_metrics"]["TestAgent"]["total_requests"] == 1
        assert len(data["recent_errors"]) > 0
    
    def test_export_metrics_markdown(self):
        """Test exporting metrics as Markdown."""
        # Add test data
        metrics_collector.record_agent_request("MarkdownAgent", True, 2.0, 200, 0.10)
        
        md_export = export_metrics("markdown")
        
        assert "# System Metrics Report" in md_export
        assert "## System Health" in md_export
        assert "## Agent Performance" in md_export
        assert "### MarkdownAgent" in md_export
        assert "Requests: 1" in md_export
    
    def test_export_metrics_invalid_format(self):
        """Test export with invalid format raises error."""
        with pytest.raises(ValueError, match="Unsupported format"):
            export_metrics("invalid_format")


class TestAlertManager:
    """Test AlertManager functionality."""
    
    def test_check_alerts_no_issues(self):
        """Test alert checking when no issues."""
        manager = AlertManager()
        
        # Set up healthy metrics
        collector = MetricsCollector()
        collector.record_agent_request("HealthyAgent", True, 1.0)
        collector.record_agent_request("HealthyAgent", True, 1.0)
        
        # Temporarily replace global collector
        original = metrics_collector.metrics
        metrics_collector.metrics = collector.metrics
        
        try:
            alerts = manager.check_alerts()
            assert len(alerts) == 0
        finally:
            metrics_collector.metrics = original
    
    def test_check_alerts_low_success_rate(self):
        """Test alert for low success rate."""
        manager = AlertManager()
        collector = MetricsCollector()
        
        # Create low success rate
        for _ in range(10):
            collector.record_agent_request("BadAgent", False, 1.0)
        
        original = metrics_collector.metrics
        metrics_collector.metrics = collector.metrics
        
        try:
            alerts = manager.check_alerts()
            assert len(alerts) > 0
            assert any(alert["type"] == "success_rate" for alert in alerts)
            assert any("low" in alert["message"] for alert in alerts)
        finally:
            metrics_collector.metrics = original
    
    def test_check_alerts_high_response_time(self):
        """Test alert for high response time."""
        manager = AlertManager()
        collector = MetricsCollector()
        
        # Create high response time
        collector.record_agent_request("SlowAgent", True, 10.0)  # 10 seconds
        
        original = metrics_collector.metrics
        metrics_collector.metrics = collector.metrics
        
        try:
            alerts = manager.check_alerts()
            assert any(alert["type"] == "response_time" for alert in alerts)
        finally:
            metrics_collector.metrics = original
    
    @patch('src.monitoring.enhanced_monitoring.logfire')
    @patch('src.monitoring.enhanced_monitoring.console')
    def test_send_alert(self, mock_console, mock_logfire):
        """Test sending alerts."""
        manager = AlertManager()
        
        alert = {
            "severity": "high",
            "type": "test_alert",
            "message": "Test alert message",
            "timestamp": "2024-01-01T00:00:00"
        }
        
        manager.send_alert(alert)
        
        # Should log to logfire
        mock_logfire.warning.assert_called_once()
        
        # Should print to console
        mock_console.print.assert_called_once()
        console_output = mock_console.print.call_args[0][0]
        assert "🚨" in console_output
        assert "Test alert message" in console_output


class TestAsyncMonitoring:
    """Test async monitoring features."""
    
    @pytest.mark.asyncio
    async def test_live_monitoring_dashboard(self):
        """Test live dashboard functionality."""
        from src.monitoring import live_monitoring_dashboard
        
        # Run for a very short time
        with patch('src.monitoring.enhanced_monitoring.console') as mock_console:
            task = asyncio.create_task(live_monitoring_dashboard(refresh_rate=0.1))
            
            # Let it run briefly
            await asyncio.sleep(0.2)
            
            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Should have created and displayed dashboard
            assert mock_console.print.called


class TestGlobalInstances:
    """Test global metrics collector and alert manager."""
    
    def test_global_metrics_collector(self):
        """Test that global metrics_collector works."""
        # Clear existing metrics
        metrics_collector.metrics.clear()
        
        metrics_collector.record_agent_request("GlobalTest", True, 1.0)
        
        assert "GlobalTest" in metrics_collector.metrics
        assert metrics_collector.metrics["GlobalTest"].total_requests == 1
    
    def test_global_alert_manager(self):
        """Test that global alert_manager works."""
        alerts = alert_manager.check_alerts()
        assert isinstance(alerts, list)