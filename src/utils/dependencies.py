"""Dependency injection utilities for agents."""

from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from ..models.configs import Settings
from ..models.schemas import AgentConfig, ConversationHistory

T = TypeVar("T", bound=BaseModel)


class DependencyContainer:
    """Container for managing agent dependencies."""
    
    def __init__(self):
        self._dependencies: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
    
    def register(self, name: str, value: Any) -> None:
        """Register a dependency value."""
        self._dependencies[name] = value
    
    def register_factory(self, name: str, factory: callable) -> None:
        """Register a factory function for creating dependencies."""
        self._factories[name] = factory
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get a dependency by name."""
        if name in self._dependencies:
            return self._dependencies[name]
        elif name in self._factories:
            # Create and cache the dependency
            value = self._factories[name]()
            self._dependencies[name] = value
            return value
        return default
    
    def get_typed(self, name: str, type_: Type[T]) -> Optional[T]:
        """Get a typed dependency."""
        value = self.get(name)
        if value is not None and isinstance(value, type_):
            return value
        return None
    
    def clear(self) -> None:
        """Clear all dependencies."""
        self._dependencies.clear()


class AgentDependencies(BaseModel):
    """Base dependencies for agents."""
    settings: Settings
    config: AgentConfig
    conversation_history: Optional[ConversationHistory] = None
    tools: Dict[str, callable] = {}
    context: Dict[str, Any] = {}
    
    class Config:
        arbitrary_types_allowed = True
    
    def add_tool(self, name: str, func: callable) -> None:
        """Add a tool to the agent."""
        self.tools[name] = func
    
    def get_tool(self, name: str) -> Optional[callable]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def update_context(self, **kwargs: Any) -> None:
        """Update the agent context."""
        self.context.update(kwargs)
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self.context.get(key, default)


class CodeAgentDependencies(AgentDependencies):
    """Dependencies specific to code agents."""
    language: str = "python"
    framework: Optional[str] = None
    linter_enabled: bool = True
    formatter_enabled: bool = True
    test_runner: Optional[str] = None


class AnalysisAgentDependencies(AgentDependencies):
    """Dependencies specific to analysis agents."""
    analysis_types: list[str] = ["quality", "security", "performance"]
    severity_threshold: str = "medium"
    include_suggestions: bool = True
    max_issues: int = 100


class ChatAgentDependencies(AgentDependencies):
    """Dependencies specific to chat agents."""
    personality: str = "helpful"
    max_conversation_length: int = 100
    enable_web_search: bool = False
    enable_code_execution: bool = False


def create_dependencies(
    agent_type: str,
    settings: Optional[Settings] = None,
    config: Optional[AgentConfig] = None,
    **kwargs: Any
) -> AgentDependencies:
    """
    Factory function to create appropriate dependencies for an agent type.
    
    Args:
        agent_type: Type of agent ("code", "analysis", "chat")
        settings: Application settings
        config: Agent configuration
        **kwargs: Additional dependency values
    
    Returns:
        Appropriate dependency container for the agent type
    """
    if settings is None:
        settings = Settings()
    
    if config is None:
        from ..models.schemas import AgentRole
        role_map = {
            "code": AgentRole.CODE_GENERATOR,
            "analysis": AgentRole.CODE_ANALYZER,
            "chat": AgentRole.CHAT_ASSISTANT,
        }
        config = AgentConfig(
            name=f"{agent_type}_agent",
            role=role_map.get(agent_type, AgentRole.CHAT_ASSISTANT)
        )
    
    base_kwargs = {
        "settings": settings,
        "config": config,
        **kwargs
    }
    
    if agent_type == "code":
        return CodeAgentDependencies(**base_kwargs)
    elif agent_type == "analysis":
        return AnalysisAgentDependencies(**base_kwargs)
    elif agent_type == "chat":
        return ChatAgentDependencies(**base_kwargs)
    else:
        return AgentDependencies(**base_kwargs)


# Global dependency container
_global_container = DependencyContainer()


def get_global_container() -> DependencyContainer:
    """Get the global dependency container."""
    return _global_container


def register_global(name: str, value: Any) -> None:
    """Register a global dependency."""
    _global_container.register(name, value)


def get_global(name: str, default: Any = None) -> Any:
    """Get a global dependency."""
    return _global_container.get(name, default)