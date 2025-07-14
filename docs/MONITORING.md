# Monitoring and Observability Guide

This guide covers the comprehensive monitoring and observability features of the Ajentik AI system.

## Overview

The system provides:
- Real-time metrics collection
- Performance monitoring
- Cost tracking
- Alert management
- Distributed tracing with Logfire
- Live dashboards

## Setup

### 1. Basic Setup (Local Metrics)

No additional setup required. Basic metrics are collected automatically.

### 2. Logfire Integration (Recommended)

1. Sign up at [https://logfire.pydantic.dev](https://logfire.pydantic.dev)
2. Create a project
3. Get your write token
4. Add to `.env`:

```env
LOGFIRE_WRITE_TOKEN=your-token-here
LOGFIRE_PROJECT=your-project-name
```

## Using the Monitoring Features

### CLI Commands

#### View Live Dashboard

```bash
ajentik monitor --live
```

Shows real-time:
- Agent performance metrics
- Tool usage statistics
- System health indicators
- Token usage and costs

#### Export Metrics

```bash
# Export as JSON
ajentik monitor --export json

# Export as Markdown report
ajentik monitor --export markdown
```

#### Check Alerts

```bash
ajentik monitor --alerts
```

### Python API

#### Basic Monitoring

```python
from src.monitoring import monitor_operation

# Monitor any operation
with monitor_operation("data_processing", agent_name="DataAgent"):
    result = await process_data()
```

#### Access Metrics

```python
from src.monitoring import metrics_collector

# Get system health
health = metrics_collector.get_system_health()
print(f"Status: {health['status']}")
print(f"Success Rate: {health['success_rate']}%")

# Get agent metrics
agent_metrics = metrics_collector.metrics["ChatAgent"]
print(f"Total Requests: {agent_metrics.total_requests}")
print(f"Average Response Time: {agent_metrics.average_response_time}s")
```

#### Custom Metrics

```python
# Record custom agent activity
metrics_collector.record_agent_request(
    agent_name="CustomAgent",
    success=True,
    response_time=1.5,
    tokens=250,
    cost=0.05
)

# Record tool usage
metrics_collector.record_tool_usage(
    tool_name="web_search",
    agent_name="ResearchAgent",
    success=True,
    execution_time=0.8
)

# Record errors
metrics_collector.record_error(
    component="DataProcessor",
    error_type="ValidationError",
    error_message="Invalid input format",
    context={"input_size": 1000}
)
```

## Metrics Collected

### Agent Metrics

- **Total Requests**: Number of requests processed
- **Success Rate**: Percentage of successful requests
- **Average Response Time**: Mean processing time
- **Token Usage**: Total tokens consumed
- **Total Cost**: Estimated API costs
- **Failure Count**: Number of failed requests

### Tool Metrics

- **Usage Count**: How often each tool is used
- **Success Rate**: Tool execution success rate
- **Execution Time**: Average tool runtime
- **Error Log**: Recent tool failures

### Model Metrics

- **Request Count**: API calls per model
- **Token Consumption**: Tokens per model
- **Latency**: Response times
- **Cost Breakdown**: Expenses per model

### System Health

- **Overall Status**: healthy/degraded/unhealthy
- **Uptime**: System running time
- **Active Agents**: Number of configured agents
- **Recent Errors**: Errors in last 5 minutes
- **Resource Usage**: Memory and CPU (if available)

## Alert System

### Default Alert Thresholds

```python
{
    "error_rate": 10.0,      # Alert if >10% errors
    "response_time": 5.0,    # Alert if >5s average
    "failure_count": 10,     # Alert if >10 failures in 5min
}
```

### Alert Types

1. **Success Rate Alerts**
   - Triggered when success rate drops below 90%
   - Severity: HIGH

2. **Response Time Alerts**
   - Triggered when average response exceeds threshold
   - Severity: MEDIUM

3. **Error Spike Alerts**
   - Triggered on sudden increase in errors
   - Severity: HIGH

4. **Cost Alerts** (configurable)
   - Triggered when costs exceed budget
   - Severity: MEDIUM

### Custom Alerts

```python
from src.monitoring import alert_manager

# Check for custom conditions
alerts = alert_manager.check_alerts()
for alert in alerts:
    if alert["severity"] == "high":
        # Take action
        send_notification(alert["message"])
```

## Logfire Integration

### Distributed Tracing

Every operation is traced:

```
User Request
  └─> Agent Processing
      ├─> Model API Call
      ├─> Tool Execution
      └─> Response Generation
```

### Viewing Traces

1. Open Logfire dashboard
2. Navigate to your project
3. Use queries to filter:

```sql
-- Agent performance
SELECT 
    attributes->>'agent' as agent,
    COUNT(*) as requests,
    AVG(duration_ms) as avg_duration
FROM spans
WHERE attributes->>'agent' IS NOT NULL
GROUP BY agent
```

### Custom Spans

```python
import logfire

with logfire.span("custom_operation", task_id=123):
    # Your code
    logfire.info("Processing started")
    result = process()
    logfire.info("Processing completed", result=result)
```

## Dashboard Layouts

### System Overview

```
┌─────────────────────────────────────┐
│      System Monitoring Dashboard     │
│  Status: HEALTHY | Uptime: 2h 15m   │
└─────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┐
│    Agents    │    Tools     │    Health    │
├──────────────┼──────────────┼──────────────┤
│ ChatAgent    │ file_reader  │ Requests: 150│
│ Reqs: 50     │ Uses: 25     │ Agents: 3    │
│ Success: 98% │ Success: 100%│ Errors: 2    │
└──────────────┴──────────────┴──────────────┘
```

### Performance Metrics

```
Agent Performance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent          Requests   Success   Avg Time
────────────   ────────   ───────   ────────
ChatAgent      125        98.4%     1.2s
CodeAgent      48         95.8%     2.5s
AnalysisAgent  73         100%      1.8s
```

## Cost Tracking

### Token Usage Report

```python
# Get cost breakdown
costs = {}
for model, metrics in metrics_collector.model_metrics.items():
    costs[model] = {
        "requests": metrics["requests"],
        "tokens": metrics["tokens"],
        "cost": metrics["cost"]
    }
```

### Budget Monitoring

```python
# Set budget alert
DAILY_BUDGET = 10.0  # $10 per day

total_cost = sum(m.total_cost for m in metrics_collector.metrics.values())
if total_cost > DAILY_BUDGET:
    send_budget_alert(total_cost)
```

## Performance Optimization

### Identifying Bottlenecks

1. Check average response times:
```python
slow_agents = [
    (name, metrics.average_response_time)
    for name, metrics in metrics_collector.metrics.items()
    if metrics.average_response_time > 3.0
]
```

2. Find failing tools:
```python
failing_tools = [
    (tool, data["success_count"] / data["usage_count"])
    for tool, data in metrics_collector.tool_metrics.items()
    if data["usage_count"] > 0 and 
       data["success_count"] / data["usage_count"] < 0.9
]
```

### Optimization Strategies

1. **Cache Frequent Requests**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_analysis(code_hash):
    return await agent.analyze_code(code)
```

2. **Batch Operations**
```python
# Process multiple items together
results = await asyncio.gather(*[
    agent.process(item) for item in items
])
```

3. **Adjust Timeouts**
```python
config = AgentConfig(
    timeout=60.0,  # Increase for complex tasks
    max_retries=2  # Reduce retries for speed
)
```

## Debugging with Monitoring

### Enable Debug Logging

```bash
ajentik --debug monitor --live
```

### Trace Specific Operations

```python
with logfire.span("debug_operation") as span:
    span.set_attribute("debug", True)
    span.set_attribute("user_id", user_id)
    
    try:
        result = await risky_operation()
    except Exception as e:
        span.set_attribute("error", str(e))
        raise
```

### Analyze Error Patterns

```python
# Group errors by type
error_types = {}
for error in metrics_collector.error_log:
    error_type = error["error_type"]
    error_types[error_type] = error_types.get(error_type, 0) + 1

# Find most common errors
sorted_errors = sorted(
    error_types.items(),
    key=lambda x: x[1],
    reverse=True
)
```

## Best Practices

### 1. Monitor Proactively

```python
# Regular health checks
async def health_monitor():
    while True:
        health = metrics_collector.get_system_health()
        if health["status"] != "healthy":
            await send_alert(health)
        await asyncio.sleep(60)  # Check every minute
```

### 2. Set Appropriate Thresholds

```python
# Adjust based on your needs
alert_manager.thresholds = {
    "error_rate": 5.0,      # Stricter error rate
    "response_time": 3.0,   # Faster response expectation
    "failure_count": 5,     # Lower tolerance
}
```

### 3. Use Context in Monitoring

```python
with monitor_operation(
    "user_request",
    agent_name="ChatAgent",
    user_id=user_id,
    request_type="support",
    priority="high"
):
    # Operation with rich context
    response = await agent.chat(message, history)
```

### 4. Export Regular Reports

```bash
# Daily metrics export
0 0 * * * /usr/bin/ajentik monitor --export markdown > /reports/daily_$(date +%Y%m%d).md
```

### 5. Correlate Metrics

Look for patterns:
- High error rates during specific times
- Correlation between response time and token usage
- Tool failures affecting agent success rates

## Troubleshooting

### No Metrics Showing

1. Check monitoring is enabled:
```python
settings = Settings()
assert settings.enable_monitoring is True
```

2. Verify Logfire setup:
```bash
ajentik --debug version
```

### Missing Traces

1. Ensure Logfire token is valid
2. Check network connectivity
3. Verify project name matches

### Performance Impact

If monitoring affects performance:

1. Disable console output:
```python
config = LogfireConfig(console=False)
```

2. Increase batching:
```python
# Batch metric updates
with metrics_collector.batch_update():
    # Multiple operations
    pass
```

3. Sample traces:
```python
import random

if random.random() < 0.1:  # 10% sampling
    with monitor_operation("sampled_op"):
        pass
```