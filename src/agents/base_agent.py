"""Base agent class with PydanticAI and Logfire integration."""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

import logfire
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.exceptions import UnexpectedModelBehavior

from ..models.schemas import (
    AgentConfig,
    AgentMetrics,
    ConversationHistory,
    Message,
    MessageRole,
    ToolResult,
)
from ..utils.dependencies import AgentDependencies
from ..utils.logfire_setup import (
    LogfireContextManager,
    log_agent_activity,
    log_model_metrics,
    log_tool_usage,
)
from ..monitoring import monitor_operation, metrics_collector

T = TypeVar("T", bound=BaseModel)
D = TypeVar("D", bound=AgentDependencies)


class BaseAgent(ABC, Generic[T, D]):
    """
    Abstract base agent with PydanticAI and Logfire integration.
    
    Type Parameters:
        T: Output type (Pydantic model)
        D: Dependencies type
    """
    
    def __init__(
        self,
        config: AgentConfig,
        output_type: Type[T],
        dependencies_type: Type[D],
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the base agent.
        
        Args:
            config: Agent configuration
            output_type: Expected output type (Pydantic model)
            dependencies_type: Type of dependencies container
            system_prompt: Optional system prompt override
        """
        self.config = config
        self.output_type = output_type
        self.dependencies_type = dependencies_type
        self.metrics = AgentMetrics(agent_name=config.name)
        
        # Use provided system prompt or generate default
        prompt = system_prompt or config.system_prompt or self.get_default_prompt()
        
        # Create PydanticAI agent
        self.agent = Agent(
            model=config.model,
            result_type=output_type,
            deps_type=dependencies_type,
            system_prompt=prompt,
            retries=config.retry_attempts,
            result_retries=config.retry_attempts,
        )
        
        # Register tools
        self._register_tools()
        
        # Log agent initialization
        log_agent_activity(
            agent_name=config.name,
            activity="initialized",
            role=config.role.value,
            model=config.model,
            tools_count=len(config.tools or [])
        )
    
    @abstractmethod
    def get_default_prompt(self) -> str:
        """Get the default system prompt for this agent type."""
        pass
    
    @abstractmethod
    def _register_tools(self) -> None:
        """Register agent-specific tools."""
        pass
    
    async def run(
        self,
        prompt: str,
        deps: D,
        conversation_history: Optional[ConversationHistory] = None,
        **kwargs: Any
    ) -> T:
        """
        Run the agent with the given prompt and dependencies.
        
        Args:
            prompt: User prompt
            deps: Agent dependencies
            conversation_history: Optional conversation history
            **kwargs: Additional arguments passed to the agent
        
        Returns:
            Validated output of type T
        """
        start_time = time.time()
        
        # Update metrics
        self.metrics.total_requests += 1
        
        # Prepare conversation context
        if conversation_history:
            deps.conversation_history = conversation_history
        
        # Create full prompt with history if available
        full_prompt = self._build_prompt_with_history(prompt, conversation_history)
        
        try:
            # Run agent with enhanced monitoring
            with monitor_operation(
                f"agent_run_{self.config.name}",
                agent_name=self.config.name,
                prompt_length=len(full_prompt)
            ):
                result = await self.agent.run(
                    full_prompt,
                    deps=deps,
                    **kwargs
                )
                
                # Extract result data
                output = result.data
                tokens_used = result.usage().total_tokens if hasattr(result, 'usage') else 0
                
                # Update metrics
                elapsed_time = time.time() - start_time
                self.metrics.successful_requests += 1
                self.metrics.total_tokens_used += tokens_used
                self.metrics.average_response_time = (
                    (self.metrics.average_response_time * (self.metrics.successful_requests - 1) + elapsed_time)
                    / self.metrics.successful_requests
                )
                
                # Record agent request in metrics collector
                metrics_collector.record_agent_request(
                    agent_name=self.config.name,
                    success=True,
                    response_time=elapsed_time,
                    tokens=tokens_used,
                    cost=self._estimate_cost(tokens_used)
                )
                
                # Record model usage
                metrics_collector.record_model_usage(
                    model=self.config.model,
                    tokens=tokens_used,
                    latency=elapsed_time,
                    cost=self._estimate_cost(tokens_used)
                )
                
                # Log success
                log_agent_activity(
                    agent_name=self.config.name,
                    activity="completed_request",
                    success=True,
                    response_time=elapsed_time,
                    tokens_used=tokens_used
                )
                
                # Log model metrics
                log_model_metrics(
                    model=self.config.model,
                    tokens_used=tokens_used,
                    response_time=elapsed_time,
                    cost=self._estimate_cost(tokens_used)
                )
                
                return output
                
        except (ModelRetry, UnexpectedModelBehavior) as e:
            self.metrics.failed_requests += 1
            log_agent_activity(
                agent_name=self.config.name,
                activity="request_failed",
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
        except Exception as e:
            self.metrics.failed_requests += 1
            log_agent_activity(
                agent_name=self.config.name,
                activity="request_failed",
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
    
    def run_sync(
        self,
        prompt: str,
        deps: D,
        conversation_history: Optional[ConversationHistory] = None,
        **kwargs: Any
    ) -> T:
        """Synchronous version of run()."""
        import asyncio
        return asyncio.run(self.run(prompt, deps, conversation_history, **kwargs))
    
    def _build_prompt_with_history(
        self,
        prompt: str,
        history: Optional[ConversationHistory]
    ) -> str:
        """Build a prompt that includes conversation history."""
        if not history or not history.messages:
            return prompt
        
        # Format history
        history_text = "\n".join([
            f"{msg.role.value}: {msg.content}"
            for msg in history.messages[-10:]  # Last 10 messages
        ])
        
        return f"""Previous conversation:
{history_text}

Current request: {prompt}"""
    
    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost based on token usage."""
        # Simplified cost estimation (would need real pricing data)
        cost_per_1k_tokens = {
            "gpt-4": 0.03,
            "gpt-4o": 0.01,
            "claude-3-5-sonnet": 0.015,
            "gemini-2.0": 0.01,
        }
        
        model_name = self.config.model.split(":", 1)[1] if ":" in self.config.model else self.config.model
        rate = cost_per_1k_tokens.get(model_name, 0.01)
        return (tokens / 1000) * rate
    
    def create_tool(
        self,
        name: str,
        description: str,
        func: callable
    ) -> None:
        """
        Create and register a tool for the agent.
        
        Args:
            name: Tool name
            description: Tool description
            func: Tool function
        """
        @self.agent.tool_plain
        async def tool_wrapper(ctx: RunContext[D], *args, **kwargs) -> Any:
            """Wrapper that adds Logfire tracking to tools."""
            start_time = time.time()
            
            try:
                # Execute tool
                result = await func(ctx, *args, **kwargs)
                
                # Log success
                execution_time = time.time() - start_time
                
                # Record tool usage in metrics collector
                metrics_collector.record_tool_usage(
                    tool_name=name,
                    agent_name=self.config.name,
                    success=True,
                    execution_time=execution_time
                )
                
                log_tool_usage(
                    tool_name=name,
                    agent_name=self.config.name,
                    success=True,
                    execution_time=execution_time
                )
                
                return result
                
            except Exception as e:
                # Log failure
                execution_time = time.time() - start_time
                
                # Record tool failure in metrics collector
                metrics_collector.record_tool_usage(
                    tool_name=name,
                    agent_name=self.config.name,
                    success=False,
                    execution_time=execution_time,
                    error=str(e)
                )
                
                log_tool_usage(
                    tool_name=name,
                    agent_name=self.config.name,
                    success=False,
                    execution_time=execution_time,
                    error=str(e)
                )
                raise
        
        # Set the tool name and description
        tool_wrapper.__name__ = name
        tool_wrapper.__doc__ = description
    
    def get_metrics(self) -> AgentMetrics:
        """Get current agent metrics."""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset agent metrics."""
        self.metrics = AgentMetrics(agent_name=self.config.name)