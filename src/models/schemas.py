"""Pydantic models for data validation across the ajentik system."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, ConfigDict


class ModelProvider(str, Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    GROQ = "groq"
    COHERE = "cohere"
    MISTRAL = "mistral"


class AgentRole(str, Enum):
    """Agent roles and specializations."""
    CODE_GENERATOR = "code_generator"
    CODE_ANALYZER = "code_analyzer"
    CHAT_ASSISTANT = "chat_assistant"
    RESEARCHER = "researcher"
    PLANNER = "planner"


class MessageRole(str, Enum):
    """Message roles in conversations."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Priority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Message(BaseModel):
    """Conversation message with validation."""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(use_enum_values=True)


class ConversationHistory(BaseModel):
    """Validated conversation history."""
    messages: List[Message]
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, role: MessageRole, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.now()


class ToolParameter(BaseModel):
    """Tool parameter specification."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolSpecification(BaseModel):
    """Tool specification for agents."""
    name: str
    description: str
    parameters: List[ToolParameter]
    returns: str
    examples: Optional[List[Dict[str, Any]]] = None


class ToolResult(BaseModel):
    """Result from tool execution."""
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float
    metadata: Optional[Dict[str, Any]] = None


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    role: AgentRole
    model: str = "openai:gpt-4o"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    enable_monitoring: bool = True
    retry_attempts: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=60, gt=0)
    
    @field_validator("model")
    def validate_model_format(cls, v: str) -> str:
        """Validate model format is provider:model_name."""
        if ":" not in v:
            raise ValueError("Model must be in format 'provider:model_name'")
        provider, model_name = v.split(":", 1)
        if provider not in [p.value for p in ModelProvider]:
            raise ValueError(f"Unknown provider: {provider}")
        return v


class CodeGenerationRequest(BaseModel):
    """Request for code generation."""
    description: str
    language: str = "python"
    framework: Optional[str] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    examples: Optional[List[str]] = None


class CodeGenerationResponse(BaseModel):
    """Response from code generation."""
    code: str
    language: str
    explanation: Optional[str] = None
    dependencies: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    confidence_score: float = Field(ge=0.0, le=1.0)


class CodeAnalysisRequest(BaseModel):
    """Request for code analysis."""
    code: str
    language: str = "python"
    analysis_types: List[str] = Field(
        default=["quality", "security", "performance"]
    )
    include_suggestions: bool = True


class CodeIssue(BaseModel):
    """Individual code issue found during analysis."""
    type: str
    severity: str
    line_number: Optional[int] = None
    description: str
    suggestion: Optional[str] = None


class CodeAnalysisResponse(BaseModel):
    """Response from code analysis."""
    summary: str
    issues: List[CodeIssue] = []
    metrics: Dict[str, Union[int, float]] = {}
    suggestions: List[str] = []
    overall_score: float = Field(ge=0.0, le=10.0)


class Task(BaseModel):
    """Task definition with validation."""
    id: str
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[AgentRole] = None
    dependencies: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def mark_completed(self, result: Any = None) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        self.result = result
    
    def mark_failed(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now()
        self.error = error


class WorkflowStep(BaseModel):
    """Step in a workflow."""
    name: str
    agent_role: AgentRole
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    timeout: int = 60
    retry_on_failure: bool = True


class Workflow(BaseModel):
    """Multi-step workflow definition."""
    name: str
    description: str
    steps: List[WorkflowStep]
    parallel_execution: bool = False
    created_at: datetime = Field(default_factory=datetime.now)


class AgentMetrics(BaseModel):
    """Performance metrics for an agent."""
    agent_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


class SystemHealth(BaseModel):
    """System health status."""
    status: str = "healthy"
    agents: Dict[str, str] = {}
    memory_usage_mb: float = 0.0
    active_tasks: int = 0
    uptime_seconds: float = 0.0
    last_error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)