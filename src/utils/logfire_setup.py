"""Logfire setup and configuration utilities."""

import os
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import logfire
from pydantic import BaseModel

from ..models.configs import LogfireConfig, Settings

T = TypeVar("T")


def setup_logfire(config: Optional[LogfireConfig] = None) -> None:
    """
    Initialize Logfire with the provided configuration.
    
    Args:
        config: Logfire configuration. If None, loads from settings.
    """
    if config is None:
        settings = Settings()
        config = settings.get_logfire_config()
    
    configure_args = {
        "service_name": config.service_name,
        "console": config.console,
    }
    
    # Set project if provided
    if config.project:
        configure_args["project_name"] = config.project
    
    # Set write token if provided
    if config.write_token:
        os.environ["LOGFIRE_WRITE_TOKEN"] = config.write_token.get_secret_value()
    
    # Configure Logfire
    logfire.configure(**configure_args)
    
    # Instrument PydanticAI
    logfire.instrument_pydantic_ai()
    
    # Log initialization
    logfire.info(
        "Logfire initialized",
        project=config.project,
        service=config.service_name,
        console_enabled=config.console
    )


def instrument_function(name: Optional[str] = None) -> Callable:
    """
    Decorator to instrument a function with Logfire tracing.
    
    Args:
        name: Optional span name. If not provided, uses function name.
    
    Returns:
        Decorated function with Logfire instrumentation.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        span_name = name or func.__name__
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            with logfire.span(span_name, _function=func.__name__):
                try:
                    result = func(*args, **kwargs)
                    logfire.info(f"{span_name} completed successfully")
                    return result
                except Exception as e:
                    logfire.error(f"{span_name} failed", error=str(e))
                    raise
        
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            with logfire.span(span_name, _function=func.__name__):
                try:
                    result = await func(*args, **kwargs)
                    logfire.info(f"{span_name} completed successfully")
                    return result
                except Exception as e:
                    logfire.error(f"{span_name} failed", error=str(e))
                    raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_agent_activity(
    agent_name: str,
    activity: str,
    **kwargs: Any
) -> None:
    """
    Log agent activity with structured data.
    
    Args:
        agent_name: Name of the agent
        activity: Description of the activity
        **kwargs: Additional context to log
    """
    logfire.info(
        f"Agent activity: {activity}",
        agent=agent_name,
        **kwargs
    )


def log_tool_usage(
    tool_name: str,
    agent_name: str,
    success: bool,
    execution_time: float,
    **kwargs: Any
) -> None:
    """
    Log tool usage by an agent.
    
    Args:
        tool_name: Name of the tool used
        agent_name: Name of the agent using the tool
        success: Whether the tool execution was successful
        execution_time: Time taken to execute the tool
        **kwargs: Additional context
    """
    level = "info" if success else "error"
    getattr(logfire, level)(
        f"Tool {tool_name} {'succeeded' if success else 'failed'}",
        tool=tool_name,
        agent=agent_name,
        success=success,
        execution_time_ms=execution_time * 1000,
        **kwargs
    )


def log_model_metrics(
    model: str,
    tokens_used: int,
    response_time: float,
    cost: float,
    **kwargs: Any
) -> None:
    """
    Log model usage metrics.
    
    Args:
        model: Model identifier
        tokens_used: Number of tokens consumed
        response_time: Response time in seconds
        cost: Estimated cost in USD
        **kwargs: Additional metrics
    """
    logfire.info(
        "Model metrics",
        model=model,
        tokens_used=tokens_used,
        response_time_ms=response_time * 1000,
        cost_usd=cost,
        **kwargs
    )


class LogfireContextManager:
    """Context manager for Logfire spans with automatic error handling."""
    
    def __init__(self, span_name: str, **attributes: Any):
        self.span_name = span_name
        self.attributes = attributes
        self.span = None
    
    def __enter__(self):
        self.span = logfire.span(self.span_name, **self.attributes).__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logfire.error(
                f"{self.span_name} failed",
                error_type=exc_type.__name__,
                error_message=str(exc_val)
            )
        if self.span:
            self.span.__exit__(exc_type, exc_val, exc_tb)
        return False
    
    async def __aenter__(self):
        self.span = logfire.span(self.span_name, **self.attributes).__enter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logfire.error(
                f"{self.span_name} failed",
                error_type=exc_type.__name__,
                error_message=str(exc_val)
            )
        if self.span:
            self.span.__exit__(exc_type, exc_val, exc_tb)
        return False


def create_dashboard_query(metric: str) -> str:
    """
    Create a SQL query for common Logfire dashboard metrics.
    
    Args:
        metric: Type of metric (e.g., "agent_performance", "tool_usage", "error_rate")
    
    Returns:
        SQL query string for the dashboard
    """
    queries = {
        "agent_performance": """
            SELECT 
                attributes->>'agent' as agent_name,
                COUNT(*) as total_requests,
                AVG(duration_ms) as avg_duration_ms,
                SUM(CASE WHEN attributes->>'success' = 'true' THEN 1 ELSE 0 END) as successful_requests
            FROM spans
            WHERE attributes->>'agent' IS NOT NULL
            GROUP BY attributes->>'agent'
            ORDER BY total_requests DESC
        """,
        "tool_usage": """
            SELECT 
                attributes->>'tool' as tool_name,
                COUNT(*) as usage_count,
                AVG(CAST(attributes->>'execution_time_ms' AS FLOAT)) as avg_execution_time_ms,
                SUM(CASE WHEN attributes->>'success' = 'true' THEN 1 ELSE 0 END) as success_count
            FROM spans
            WHERE attributes->>'tool' IS NOT NULL
            GROUP BY attributes->>'tool'
            ORDER BY usage_count DESC
        """,
        "error_rate": """
            SELECT 
                DATE_TRUNC('hour', created_at) as hour,
                COUNT(CASE WHEN level = 'error' THEN 1 END) as error_count,
                COUNT(*) as total_count,
                ROUND(COUNT(CASE WHEN level = 'error' THEN 1 END)::FLOAT / COUNT(*) * 100, 2) as error_rate
            FROM spans
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour DESC
        """,
        "model_costs": """
            SELECT 
                attributes->>'model' as model,
                SUM(CAST(attributes->>'tokens_used' AS INT)) as total_tokens,
                SUM(CAST(attributes->>'cost_usd' AS FLOAT)) as total_cost_usd,
                COUNT(*) as request_count
            FROM spans
            WHERE attributes->>'model' IS NOT NULL
                AND attributes->>'tokens_used' IS NOT NULL
            GROUP BY attributes->>'model'
            ORDER BY total_cost_usd DESC
        """
    }
    
    return queries.get(metric, "SELECT * FROM spans LIMIT 10")


# Import asyncio only when needed
import asyncio