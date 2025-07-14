# API Reference

Complete API documentation for the Ajentik AI System.

## Table of Contents

- [Agents](#agents)
  - [BaseAgent](#baseagent)
  - [ChatAgent](#chatagent)
  - [CodeAgent](#codeagent)
  - [AnalysisAgent](#analysisagent)
- [Models](#models)
  - [Configuration Models](#configuration-models)
  - [Schema Models](#schema-models)
- [Monitoring](#monitoring)
  - [MetricsCollector](#metricscollector)
  - [AlertManager](#alertmanager)
- [Utilities](#utilities)

## Agents

### BaseAgent

Abstract base class for all agents.

```python
from src.agents.base_agent import BaseAgent

class BaseAgent(ABC, Generic[T, D]):
    """
    Abstract base agent with PydanticAI and Logfire integration.
    
    Type Parameters:
        T: Output type (Pydantic model)
        D: Dependencies type
    """
```

#### Methods

##### `__init__(config, output_type, dependencies_type, system_prompt)`

Initialize the base agent.

**Parameters:**
- `config` (AgentConfig): Agent configuration
- `output_type` (Type[T]): Expected output model type
- `dependencies_type` (Type[D]): Dependencies class type
- `system_prompt` (Optional[str]): System message for the agent

##### `async run(prompt, deps, conversation_history, **kwargs) -> T`

Run the agent asynchronously.

**Parameters:**
- `prompt` (str): User prompt
- `deps` (D): Agent dependencies
- `conversation_history` (Optional[ConversationHistory]): Previous messages
- `**kwargs`: Additional arguments for the agent

**Returns:** Validated output of type T

##### `run_sync(prompt, deps, conversation_history, **kwargs) -> T`

Synchronous version of run().

##### `get_metrics() -> AgentMetrics`

Get current agent metrics.

**Returns:** AgentMetrics object with performance data

### ChatAgent

Agent for conversational interactions.

```python
from src.agents import ChatAgent

agent = ChatAgent(config: Optional[AgentConfig] = None)
```

#### Methods

##### `async chat(message, conversation_history) -> ChatResponse`

Process a chat message.

**Parameters:**
- `message` (str): User message
- `conversation_history` (ConversationHistory): Chat history

**Returns:** ChatResponse with message, confidence, and suggestions

**Example:**
```python
response = await agent.chat(
    "Hello, how are you?",
    ConversationHistory(messages=[], session_id="123")
)
print(response.message)
print(f"Confidence: {response.confidence}")
```

##### `chat_sync(message, conversation_history) -> ChatResponse`

Synchronous version of chat().

### CodeAgent

Agent for code generation tasks.

```python
from src.agents import CodeAgent

agent = CodeAgent(config: Optional[AgentConfig] = None)
```

#### Methods

##### `async generate_code(request) -> CodeGenerationResponse`

Generate code based on request.

**Parameters:**
- `request` (CodeGenerationRequest): Code generation specifications

**Returns:** CodeGenerationResponse with generated code

**Example:**
```python
request = CodeGenerationRequest(
    description="Create a REST API endpoint",
    language="python",
    framework="fastapi",
    requirements=["Authentication", "Validation"]
)

response = await agent.generate_code(request)
print(response.code)
```

### AnalysisAgent

Agent for code analysis tasks.

```python
from src.agents import AnalysisAgent

agent = AnalysisAgent(config: Optional[AgentConfig] = None)
```

#### Methods

##### `async analyze_code(request) -> CodeAnalysisResponse`

Analyze code for issues.

**Parameters:**
- `request` (CodeAnalysisRequest): Analysis specifications

**Returns:** CodeAnalysisResponse with issues and score

**Example:**
```python
request = CodeAnalysisRequest(
    code="def add(a, b): return a + b",
    language="python",
    analysis_types=["quality", "security"]
)

response = await agent.analyze_code(request)
for issue in response.issues:
    print(f"{issue.severity}: {issue.description}")
```

## Models

### Configuration Models

#### AgentConfig

Configuration for agents.

```python
class AgentConfig(BaseModel):
    name: str
    model: str = "openai:gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: float = 30.0
    max_retries: int = 3
    system_message: Optional[str] = None
```

#### Settings

Application settings from environment.

```python
class Settings(BaseSettings):
    # API Keys
    openai_api_key: Optional[SecretStr] = None
    anthropic_api_key: Optional[SecretStr] = None
    google_api_key: Optional[SecretStr] = None
    
    # Model Settings
    default_model: str = "openai:gpt-4o"
    default_temperature: float = 0.7
    default_max_tokens: int = 1000
    
    # Features
    enable_monitoring: bool = True
    enable_caching: bool = True
```

### Schema Models

#### Message

Chat message representation.

```python
class Message(BaseModel):
    role: MessageRole  # USER, ASSISTANT, or SYSTEM
    content: str
    timestamp: Optional[datetime] = None
```

#### ConversationHistory

```python
class ConversationHistory(BaseModel):
    messages: List[Message]
    session_id: str
    metadata: Dict[str, Any] = {}
```

#### ChatResponse

```python
class ChatResponse(BaseModel):
    message: str
    confidence: float
    suggested_actions: Optional[List[str]] = None
```

#### CodeGenerationRequest

```python
class CodeGenerationRequest(BaseModel):
    description: str
    language: str
    framework: Optional[str] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    examples: Optional[List[str]] = None
```

#### CodeGenerationResponse

```python
class CodeGenerationResponse(BaseModel):
    code: str
    language: str
    framework: Optional[str] = None
    explanation: Optional[str] = None
    dependencies: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
```

#### CodeAnalysisRequest

```python
class CodeAnalysisRequest(BaseModel):
    code: str
    language: str
    analysis_types: List[str] = ["quality", "security", "performance"]
    include_suggestions: bool = True
    context: Optional[str] = None
```

#### CodeIssue

```python
class CodeIssue(BaseModel):
    type: str  # security, quality, performance, etc.
    severity: IssueSeverity  # HIGH, MEDIUM, LOW
    description: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    suggestion: Optional[str] = None
```

#### CodeAnalysisResponse

```python
class CodeAnalysisResponse(BaseModel):
    summary: str
    issues: List[CodeIssue]
    overall_score: float  # 0-10
    metrics: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None
    security_score: Optional[float] = None
    quality_score: Optional[float] = None
    performance_score: Optional[float] = None
```

## Monitoring

### MetricsCollector

Collects and aggregates system metrics.

```python
from src.monitoring import metrics_collector
```

#### Methods

##### `record_agent_request(agent_name, success, response_time, tokens, cost)`

Record an agent request.

**Parameters:**
- `agent_name` (str): Name of the agent
- `success` (bool): Whether request succeeded
- `response_time` (float): Time in seconds
- `tokens` (int): Tokens used (optional)
- `cost` (float): Estimated cost (optional)

##### `record_tool_usage(tool_name, agent_name, success, execution_time, error)`

Record tool usage.

##### `record_model_usage(model, tokens, latency, cost)`

Record model API usage.

##### `get_system_health() -> Dict[str, Any]`

Get overall system health metrics.

**Returns:** Dictionary with health indicators

### AlertManager

Manages system alerts.

```python
from src.monitoring import alert_manager
```

#### Methods

##### `check_alerts() -> List[Dict[str, Any]]`

Check for active alert conditions.

**Returns:** List of alert dictionaries

##### `send_alert(alert)`

Send/log an alert.

### monitor_operation

Context manager for monitoring operations.

```python
from src.monitoring import monitor_operation

with monitor_operation("my_operation", agent_name="MyAgent"):
    # Your code here
    result = await agent.process(data)
```

## Utilities

### Dependencies

#### AgentDependencies

Base dependencies class.

```python
class AgentDependencies(BaseModel):
    settings: Settings = Field(default_factory=Settings)
    monitoring_enabled: bool = True
    conversation_history: Optional[ConversationHistory] = None
```

#### ChatDependencies

```python
class ChatDependencies(AgentDependencies):
    enable_suggestions: bool = True
    max_history_length: int = 50
    personality: str = "helpful"
```

#### CodeDependencies

```python
class CodeDependencies(AgentDependencies):
    target_language: Optional[str] = None
    framework: Optional[str] = None
    include_tests: bool = False
    style_guide: Optional[str] = None
```

### Logfire Setup

#### setup_logfire

Initialize Logfire monitoring.

```python
from src.utils import setup_logfire

setup_logfire(config: Optional[LogfireConfig] = None)
```

#### instrument_function

Decorator for function instrumentation.

```python
from src.utils.logfire_setup import instrument_function

@instrument_function("my_function")
async def my_function():
    # Function is now monitored
    pass
```

## Error Handling

All agents may raise these exceptions:

- `ModelRetry`: Temporary model failure, can retry
- `UnexpectedModelBehavior`: Model produced invalid output
- `ValidationError`: Input validation failed
- `TimeoutError`: Request timed out
- `AuthenticationError`: API key issues

Example error handling:

```python
try:
    response = await agent.chat(message, history)
except ModelRetry as e:
    # Retry logic
    pass
except ValidationError as e:
    # Handle invalid input
    print(f"Invalid input: {e}")
except Exception as e:
    # General error
    print(f"Error: {e}")
```

## Best Practices

### 1. Always Use Context Managers

```python
async with monitor_operation("task", agent_name="Agent"):
    result = await agent.run(prompt)
```

### 2. Handle Conversation History

```python
# Maintain history for context
history = ConversationHistory(messages=[], session_id="unique-id")

# Add messages after each interaction
history.messages.append(
    Message(role=MessageRole.USER, content=user_input)
)
```

### 3. Configure Agents Appropriately

```python
# For focused tasks
config = AgentConfig(
    name="PreciseAgent",
    temperature=0.1,  # Low temperature for consistency
    max_tokens=500    # Limit response length
)
```

### 4. Monitor Performance

```python
# Check metrics regularly
metrics = agent.get_metrics()
if metrics.success_rate < 90:
    # Alert or adjust configuration
    pass
```

### 5. Use Type Hints

```python
async def process_code(
    request: CodeGenerationRequest
) -> CodeGenerationResponse:
    agent = CodeAgent()
    return await agent.generate_code(request)
```