"""Ajentik AI System - A powerful AI agent framework with CLI interface."""

__version__ = "0.1.0"
__author__ = "Ajenitk Team"
__email__ = "team@ajenitk.com"

# Make key components easily importable
from .agents import ChatAgent, CodeAgent, AnalysisAgent
from .models import (
    AgentConfig,
    ConversationHistory,
    Message,
    ChatResponse,
    CodeGenerationRequest,
    CodeGenerationResponse,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
)
from .monitoring import metrics_collector, monitor_operation
from .utils import setup_logfire

__all__ = [
    # Agents
    "ChatAgent",
    "CodeAgent", 
    "AnalysisAgent",
    # Models
    "AgentConfig",
    "ConversationHistory",
    "Message",
    "ChatResponse",
    "CodeGenerationRequest",
    "CodeGenerationResponse",
    "CodeAnalysisRequest",
    "CodeAnalysisResponse",
    # Monitoring
    "metrics_collector",
    "monitor_operation",
    # Utils
    "setup_logfire",
]