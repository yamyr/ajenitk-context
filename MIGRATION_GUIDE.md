# Ajentik Refactoring Migration Guide

This guide helps you migrate from the original Ajentik implementation to the refactored version with improved architecture, type safety, and error handling.

## Overview of Changes

The refactoring brings several improvements:
- **Better separation of concerns** - Each module has a single, clear responsibility
- **Enhanced type safety** - Comprehensive type hints and validation
- **Improved error handling** - Custom exception hierarchy with context
- **Performance optimizations** - Async support, caching, and indexing
- **Centralized utilities** - Shared code extracted to utility modules

## File Mapping

### Core Files
- `src/tools/base.py` → `src/tools/base_refactored.py`
- `src/tools/registry.py` → `src/tools/registry_refactored.py`
- `src/tools/decorators.py` → `src/tools/decorators_refactored.py`

### New Files
- `src/exceptions.py` - Custom exception hierarchy
- `src/utils/retry.py` - Retry logic with exponential backoff
- `src/utils/type_mapping.py` - Type conversion utilities
- `src/utils/validation.py` - Parameter validation
- `src/utils/logging.py` - Centralized logging

## API Changes

### 1. Tool Base Classes

#### Old
```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
```

#### New
```python
class Tool(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        pass
    
    @abstractmethod
    def _execute_impl(self, **kwargs) -> Any:
        pass
    
    # execute() is now implemented in base class with validation
```

### 2. ToolResult Changes

#### Old
```python
class ToolResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
```

#### New
```python
@dataclass
class ToolResult(Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None
    
    def unwrap(self) -> T:
        """Get data or raise exception."""
    
    def map(self, func: callable) -> 'ToolResult':
        """Map function over result."""
```

### 3. Tool Registration

#### Old
```python
registry = ToolRegistry()
registry.register_tool(tool_instance)
```

#### New
```python
registry = ToolRegistry(security_level=SecurityLevel.SAFE)
registry.register(tool_instance, aliases=["alias1", "alias2"])
# Can also register tool classes
registry.register(ToolClass)
```

### 4. Decorators

#### Old
```python
@tool(name="my_tool", description="Does something")
def my_tool(param: str) -> dict:
    return {"result": param}
```

#### New
```python
@tool(
    name="my_tool",
    description="Does something",
    tags=["utility"],
    category="text",
    version="2.0.0"
)
def my_tool(param: str) -> dict:
    return {"result": param}

# Access tool instance
tool_instance = my_tool.tool
```

### 5. Error Handling

#### Old
```python
try:
    result = tool.execute(**params)
except Exception as e:
    # Generic error handling
    pass
```

#### New
```python
from ajentik.exceptions import (
    ToolExecutionError, 
    ToolValidationError,
    SecurityError
)

try:
    result = tool.execute(**params)
except ToolValidationError as e:
    # Handle validation error
    print(f"Invalid parameter {e.parameter_name}: {e.message}")
except ToolExecutionError as e:
    # Handle execution error
    print(f"Tool {e.tool_name} failed: {e.message}")
except SecurityError as e:
    # Handle security violation
    print(f"Security level {e.security_level} blocked: {e.attempted_action}")
```

## Migration Steps

### Step 1: Update Imports

```python
# Old
from ajentik.tools import Tool, ToolResult, tool

# New
from ajentik.tools.base_refactored import Tool, ToolResult, ToolMetadata, ToolParameter
from ajentik.tools.decorators_refactored import tool
from ajentik.exceptions import ToolError, ToolExecutionError
```

### Step 2: Update Tool Implementations

```python
# Old implementation
class MyTool(Tool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "My custom tool"
    
    def execute(self, text: str) -> ToolResult:
        try:
            result = text.upper()
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

```python
# New implementation
class MyTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            description="My custom tool",
            tags=["text", "utility"],
            category="text_processing"
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="text",
                type=ToolParameterType.STRING,
                description="Text to process",
                required=True
            )
        ]
    
    def _execute_impl(self, **kwargs) -> str:
        # Validation is handled by base class
        return kwargs["text"].upper()
```

### Step 3: Update Registry Usage

```python
# Old
registry = ToolRegistry()
registry.register_tool(MyTool())
tool = registry.get_tool("my_tool")
result = registry.execute_tool("my_tool", text="hello")

# New
registry = ToolRegistry(security_level=SecurityLevel.SAFE)
registry.register(MyTool)  # Can register class directly
tool = registry.get("my_tool")
result = registry.execute("my_tool", text="hello")

# New features
tools = registry.search("text")  # Search tools
tools = registry.get_by_category("text_processing")
tools = registry.get_by_tag("utility")
stats = registry.get_statistics("my_tool")
```

### Step 4: Update Async Tools

```python
# Old
class AsyncTool(Tool):
    async def execute_async(self, **kwargs) -> ToolResult:
        # Implementation
        pass

# New
from ajentik.tools.base_refactored import AsyncTool

class MyAsyncTool(AsyncTool):
    async def _execute_impl_async(self, **kwargs) -> Any:
        # Implementation
        pass
```

### Step 5: Use New Utilities

```python
# Retry logic
from ajentik.utils.retry import retry_async, with_retry

@with_retry(max_attempts=3, exceptions=(ConnectionError,))
async def fetch_data(url: str):
    # Will retry on ConnectionError
    pass

# Type mapping
from ajentik.utils.type_mapping import python_type_to_parameter_type

param_type = python_type_to_parameter_type(List[str])  # Returns ToolParameterType.ARRAY

# Validation
from ajentik.utils.validation import validate_parameters

validated = validate_parameters(raw_params, tool.parameters)
```

## Testing Your Migration

1. **Run existing tests** to ensure compatibility
2. **Add new tests** for enhanced features:

```python
# Test new error types
def test_tool_validation():
    with pytest.raises(ToolValidationError) as exc_info:
        tool.execute(invalid_param="value")
    
    assert exc_info.value.parameter_name == "invalid_param"

# Test security levels
def test_security_enforcement():
    registry = ToolRegistry(security_level=SecurityLevel.SAFE)
    dangerous_tool = DangerousTool()  # Has "dangerous" tag
    registry.register(dangerous_tool)
    
    with pytest.raises(SecurityError):
        registry.execute("dangerous_tool")

# Test statistics
def test_execution_statistics():
    registry.execute("my_tool", text="test")
    stats = registry.get_statistics("my_tool")
    
    assert stats["total_executions"] == 1
    assert stats["successful_executions"] == 1
```

## Rollback Plan

If you need to rollback:

1. Keep old files alongside new ones during migration
2. Use feature flags to switch between implementations:

```python
USE_REFACTORED = os.getenv("USE_REFACTORED_AJENTIK", "false").lower() == "true"

if USE_REFACTORED:
    from ajentik.tools.base_refactored import Tool
else:
    from ajentik.tools.base import Tool
```

## Performance Considerations

The refactored version includes several performance improvements:

1. **Registry indexing** - O(1) lookups by category/tag
2. **Weak references** - Reduced memory usage
3. **Async support** - Better I/O handling
4. **Caching** - Tool discovery results cached

Monitor performance during migration:

```python
import time

start = time.time()
result = registry.execute("my_tool", **params)
execution_time = time.time() - start

# Compare with tool statistics
stats = registry.get_statistics("my_tool")
avg_time = stats["total_execution_time"] / stats["total_executions"]
```

## Common Issues and Solutions

### Issue 1: Import Errors
```python
# Error: ImportError: cannot import name 'Tool' from 'ajentik.tools'

# Solution: Update imports to use refactored modules
from ajentik.tools.base_refactored import Tool
```

### Issue 2: Missing Metadata
```python
# Error: AttributeError: 'MyTool' object has no attribute 'metadata'

# Solution: Implement metadata property
@property
def metadata(self) -> ToolMetadata:
    return ToolMetadata(name=self.name, description=self.description)
```

### Issue 3: Validation Errors
```python
# Error: ToolValidationError: Unknown parameters: old_param

# Solution: Update parameter definitions
@property
def parameters(self) -> List[ToolParameter]:
    return [
        ToolParameter(name="new_param", type=ToolParameterType.STRING, ...)
    ]
```

## Support

For help with migration:
1. Check the test files for examples
2. Review the docstrings in refactored modules
3. Use type hints for guidance
4. File issues with specific migration problems