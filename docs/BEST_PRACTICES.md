# Best Practices Guide

This guide covers best practices for using the Ajentik AI system effectively and efficiently.

## Agent Configuration

### 1. Choose the Right Model

Different models excel at different tasks:

```python
# For creative tasks
creative_config = AgentConfig(
    model="openai:gpt-4",
    temperature=0.8,  # Higher for creativity
    max_tokens=2000
)

# For analytical tasks
analytical_config = AgentConfig(
    model="anthropic:claude-3-5-sonnet",
    temperature=0.2,  # Lower for consistency
    max_tokens=1000
)

# For quick responses
fast_config = AgentConfig(
    model="openai:gpt-4o",  # Optimized model
    temperature=0.5,
    max_tokens=500,
    timeout=10.0  # Shorter timeout
)
```

### 2. Set Appropriate Temperatures

- **0.0-0.3**: Factual, consistent responses (analysis, calculations)
- **0.4-0.7**: Balanced (general chat, code generation)
- **0.8-1.0**: Creative, varied responses (brainstorming, creative writing)

### 3. Manage Token Usage

```python
# Limit tokens for cost control
budget_config = AgentConfig(
    max_tokens=500,  # Reasonable limit
    system_message="Be concise in responses."
)

# Track usage
metrics = agent.get_metrics()
tokens_per_request = metrics.total_tokens_used / metrics.total_requests
```

## Conversation Management

### 1. Maintain Context Effectively

```python
# Keep relevant history
MAX_HISTORY_LENGTH = 20

def trim_history(history: ConversationHistory) -> ConversationHistory:
    """Keep only recent messages."""
    if len(history.messages) > MAX_HISTORY_LENGTH:
        # Keep system message + recent messages
        history.messages = history.messages[-MAX_HISTORY_LENGTH:]
    return history
```

### 2. Use Session IDs

```python
import uuid
from datetime import datetime

# Create meaningful session IDs
session_id = f"chat_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

conversation = ConversationHistory(
    messages=[],
    session_id=session_id,
    metadata={
        "user_id": user_id,
        "purpose": "technical_support",
        "created_at": datetime.now().isoformat()
    }
)
```

### 3. Save Important Conversations

```python
import json
from pathlib import Path

def save_conversation(history: ConversationHistory, filepath: Path):
    """Save conversation with metadata."""
    data = {
        "session_id": history.session_id,
        "metadata": history.metadata,
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": getattr(msg, 'timestamp', datetime.now()).isoformat()
            }
            for msg in history.messages
        ],
        "summary": generate_summary(history)  # Optional
    }
    
    filepath.write_text(json.dumps(data, indent=2))
```

## Code Generation

### 1. Provide Clear Requirements

```python
# Good: Specific and detailed
request = CodeGenerationRequest(
    description="Create a Python function that validates email addresses",
    language="python",
    requirements=[
        "Use regex for validation",
        "Handle common edge cases",
        "Return tuple of (is_valid, error_message)",
        "Include docstring with examples"
    ],
    constraints=[
        "No external dependencies",
        "Python 3.8+ compatible"
    ],
    examples=["user@example.com", "invalid.email"]
)

# Bad: Vague
request = CodeGenerationRequest(
    description="Make email validator",
    language="python"
)
```

### 2. Specify Framework When Relevant

```python
# Framework-specific generation
frameworks = {
    "web": "fastapi",
    "data": "pandas",
    "ml": "scikit-learn",
    "ui": "react"
}

request = CodeGenerationRequest(
    description="Create a REST endpoint for user authentication",
    language="python",
    framework="fastapi",
    requirements=[
        "JWT token generation",
        "Password hashing with bcrypt",
        "Input validation with Pydantic"
    ]
)
```

### 3. Review and Test Generated Code

```python
async def generate_and_validate(request: CodeGenerationRequest):
    """Generate code and validate it."""
    # Generate
    response = await code_agent.generate_code(request)
    
    # Save to temp file
    temp_file = Path(f"temp_{request.language}")
    temp_file.write_text(response.code)
    
    # Analyze for issues
    analysis_request = CodeAnalysisRequest(
        code=response.code,
        language=request.language,
        analysis_types=["security", "quality"]
    )
    
    analysis = await analysis_agent.analyze_code(analysis_request)
    
    # Check if acceptable
    if analysis.overall_score < 7.0:
        print("Generated code has issues:")
        for issue in analysis.issues:
            print(f"- {issue.description}")
    
    return response, analysis
```

## Code Analysis

### 1. Regular Code Reviews

```python
import subprocess
from pathlib import Path

async def analyze_changed_files():
    """Analyze files changed in current branch."""
    # Get changed files
    result = subprocess.run(
        ["git", "diff", "--name-only", "main"],
        capture_output=True,
        text=True
    )
    
    changed_files = result.stdout.strip().split('\n')
    
    for file in changed_files:
        if file.endswith(('.py', '.js', '.ts')):
            request = CodeAnalysisRequest(
                code=Path(file).read_text(),
                language=file.split('.')[-1],
                analysis_types=["quality", "security"]
            )
            
            response = await analysis_agent.analyze_code(request)
            
            if response.issues:
                print(f"\n{file}: {len(response.issues)} issues found")
                for issue in response.issues[:3]:  # Top 3 issues
                    print(f"  - {issue.severity}: {issue.description}")
```

### 2. Focus Analysis Types

```python
# Security-focused for sensitive code
security_request = CodeAnalysisRequest(
    code=auth_code,
    language="python",
    analysis_types=["security"],
    context="Authentication module"
)

# Performance-focused for bottlenecks  
perf_request = CodeAnalysisRequest(
    code=data_processing_code,
    language="python",
    analysis_types=["performance"],
    context="Processes 1M records daily"
)
```

### 3. Track Code Quality Over Time

```python
from datetime import datetime

async def track_code_quality(project_path: Path):
    """Track project code quality metrics."""
    metrics = {
        "date": datetime.now().isoformat(),
        "files": {},
        "overall_score": 0
    }
    
    python_files = project_path.glob("**/*.py")
    scores = []
    
    for file in python_files:
        if "test" not in str(file):  # Skip test files
            request = CodeAnalysisRequest(
                code=file.read_text(),
                language="python",
                analysis_types=["quality"]
            )
            
            response = await analysis_agent.analyze_code(request)
            
            metrics["files"][str(file)] = {
                "score": response.overall_score,
                "issues": len(response.issues)
            }
            scores.append(response.overall_score)
    
    metrics["overall_score"] = sum(scores) / len(scores) if scores else 0
    
    # Save metrics
    metrics_file = Path("code_quality_metrics.json")
    existing = json.loads(metrics_file.read_text()) if metrics_file.exists() else []
    existing.append(metrics)
    metrics_file.write_text(json.dumps(existing, indent=2))
    
    return metrics
```

## Performance Optimization

### 1. Use Async Operations

```python
# Good: Parallel processing
async def process_multiple_files(files: List[Path]):
    """Process files in parallel."""
    tasks = []
    
    for file in files:
        request = CodeAnalysisRequest(
            code=file.read_text(),
            language=file.suffix[1:]
        )
        tasks.append(analysis_agent.analyze_code(request))
    
    # Process all files concurrently
    results = await asyncio.gather(*tasks)
    return results

# Bad: Sequential processing
def process_files_slowly(files: List[Path]):
    results = []
    for file in files:
        # This is much slower
        result = analysis_agent.analyze_code_sync(request)
        results.append(result)
    return results
```

### 2. Implement Caching

```python
from functools import lru_cache
import hashlib

class CachedAgent(ChatAgent):
    def __init__(self):
        super().__init__()
        self._cache = {}
    
    async def chat_cached(self, message: str, history: ConversationHistory):
        """Chat with caching for repeated questions."""
        # Create cache key
        cache_key = hashlib.md5(
            f"{message}:{len(history.messages)}".encode()
        ).hexdigest()
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Get response
        response = await self.chat(message, history)
        
        # Cache for 1 hour
        self._cache[cache_key] = response
        
        return response
```

### 3. Batch Operations

```python
async def batch_code_generation(requests: List[CodeGenerationRequest]):
    """Generate multiple code pieces efficiently."""
    # Group by language for better context
    by_language = {}
    for req in requests:
        by_language.setdefault(req.language, []).append(req)
    
    results = []
    
    for language, lang_requests in by_language.items():
        # Create specialized agent for language
        config = AgentConfig(
            name=f"{language}_specialist",
            system_message=f"You are an expert {language} developer."
        )
        agent = CodeAgent(config)
        
        # Process in parallel
        tasks = [agent.generate_code(req) for req in lang_requests]
        lang_results = await asyncio.gather(*tasks)
        results.extend(lang_results)
    
    return results
```

## Error Handling

### 1. Graceful Degradation

```python
async def safe_chat(agent: ChatAgent, message: str, history: ConversationHistory):
    """Chat with fallback options."""
    try:
        # Try primary model
        return await agent.chat(message, history)
    
    except (TimeoutError, ModelRetry) as e:
        # Fallback to faster model
        fallback_config = AgentConfig(
            model="openai:gpt-4o",
            max_tokens=300,
            timeout=10.0
        )
        fallback_agent = ChatAgent(fallback_config)
        
        try:
            return await fallback_agent.chat(message, history)
        except Exception:
            # Final fallback
            return ChatResponse(
                message="I'm having trouble processing your request. Please try again.",
                confidence=0.0
            )
```

### 2. Retry with Backoff

```python
import asyncio
from typing import TypeVar, Callable

T = TypeVar('T')

async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0
) -> T:
    """Retry function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            delay = base_delay * (2 ** attempt)
            print(f"Attempt {attempt + 1} failed, retrying in {delay}s...")
            await asyncio.sleep(delay)
```

### 3. Comprehensive Logging

```python
import logging
from src.monitoring import monitor_operation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def monitored_operation(agent_name: str, operation: str):
    """Operation with full monitoring."""
    with monitor_operation(operation, agent_name=agent_name) as span:
        try:
            logger.info(f"Starting {operation}")
            
            # Your operation
            result = await perform_operation()
            
            logger.info(f"Completed {operation} successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed {operation}: {e}", exc_info=True)
            
            # Record in monitoring
            metrics_collector.record_error(
                component=agent_name,
                error_type=type(e).__name__,
                error_message=str(e),
                context={"operation": operation}
            )
            raise
```

## Security Best Practices

### 1. Never Expose API Keys

```python
# Good: Use environment variables
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Bad: Hardcoded keys
api_key = "sk-..."  # NEVER DO THIS
```

### 2. Validate Generated Code

```python
async def validate_generated_code(code: str, language: str) -> bool:
    """Validate generated code for security issues."""
    # Check for dangerous patterns
    dangerous_patterns = {
        "python": [
            "eval(",
            "exec(",
            "__import__",
            "os.system",
            "subprocess.call"
        ],
        "javascript": [
            "eval(",
            "Function(",
            "innerHTML",
            "document.write"
        ]
    }
    
    patterns = dangerous_patterns.get(language, [])
    
    for pattern in patterns:
        if pattern in code:
            logger.warning(f"Dangerous pattern found: {pattern}")
            return False
    
    return True
```

### 3. Sanitize User Input

```python
def sanitize_input(user_input: str) -> str:
    """Sanitize user input for safety."""
    # Remove potential injection attempts
    sanitized = user_input.strip()
    
    # Limit length
    MAX_LENGTH = 10000
    if len(sanitized) > MAX_LENGTH:
        sanitized = sanitized[:MAX_LENGTH]
    
    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')
    
    return sanitized
```

## Cost Management

### 1. Monitor Token Usage

```python
class CostTracker:
    """Track and limit API costs."""
    
    def __init__(self, daily_budget: float = 10.0):
        self.daily_budget = daily_budget
        self.daily_cost = 0.0
        self.last_reset = datetime.now().date()
    
    def check_budget(self) -> bool:
        """Check if within budget."""
        # Reset daily counter
        if datetime.now().date() > self.last_reset:
            self.daily_cost = 0.0
            self.last_reset = datetime.now().date()
        
        return self.daily_cost < self.daily_budget
    
    def add_cost(self, tokens: int, model: str):
        """Add cost for tokens used."""
        # Approximate costs per 1K tokens
        costs = {
            "gpt-4": 0.03,
            "gpt-4o": 0.01,
            "claude-3-5-sonnet": 0.015
        }
        
        rate = costs.get(model, 0.01)
        cost = (tokens / 1000) * rate
        self.daily_cost += cost
        
        if self.daily_cost > self.daily_budget:
            raise Exception(f"Daily budget exceeded: ${self.daily_cost:.2f}")
```

### 2. Use Appropriate Models

```python
def select_model_for_task(task_type: str) -> str:
    """Select most cost-effective model for task."""
    model_selection = {
        "simple_chat": "openai:gpt-4o",      # Fast and cheap
        "code_generation": "openai:gpt-4",   # Better for code
        "analysis": "anthropic:claude-3-5-sonnet",  # Good reasoning
        "creative": "openai:gpt-4",          # Creative tasks
    }
    
    return model_selection.get(task_type, "openai:gpt-4o")
```

### 3. Cache Expensive Operations

```python
from datetime import datetime, timedelta

class ResponseCache:
    """Cache for expensive API responses."""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached response."""
        if key in self.cache:
            response, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return response
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Cache response."""
        self.cache[key] = (value, datetime.now())
    
    def clear_expired(self):
        """Remove expired entries."""
        now = datetime.now()
        expired = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp >= self.ttl
        ]
        for key in expired:
            del self.cache[key]
```