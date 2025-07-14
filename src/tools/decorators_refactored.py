"""Refactored decorators for easy tool creation.

This module provides decorators that simplify tool creation with
automatic parameter extraction and validation.
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints
import asyncio

from ..exceptions import ToolError
from ..utils.type_mapping import python_type_to_parameter_type
from ..utils.logging import get_logger
from .base_refactored import (
    Tool, AsyncTool, ToolMetadata, ToolParameter, 
    ToolParameterType, ToolResult
)

logger = get_logger(__name__)


class DecoratedTool(Tool):
    """Tool created from a decorated function."""
    
    def __init__(self, 
                 func: Callable,
                 metadata: ToolMetadata,
                 parameters: List[ToolParameter]):
        """Initialize decorated tool.
        
        Args:
            func: The decorated function
            metadata: Tool metadata
            parameters: Tool parameters
        """
        self._func = func
        self._metadata = metadata
        self._parameters = parameters
        super().__init__()
    
    @property
    def metadata(self) -> ToolMetadata:
        """Tool metadata."""
        return self._metadata
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        return self._parameters
    
    def _execute_impl(self, **kwargs) -> Any:
        """Execute the decorated function."""
        return self._func(**kwargs)


class DecoratedAsyncTool(AsyncTool):
    """Async tool created from a decorated function."""
    
    def __init__(self,
                 func: Callable,
                 metadata: ToolMetadata,
                 parameters: List[ToolParameter]):
        """Initialize decorated async tool.
        
        Args:
            func: The decorated async function
            metadata: Tool metadata
            parameters: Tool parameters
        """
        self._func = func
        self._metadata = metadata
        self._parameters = parameters
        super().__init__()
    
    @property
    def metadata(self) -> ToolMetadata:
        """Tool metadata."""
        return self._metadata
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        return self._parameters
    
    async def _execute_impl_async(self, **kwargs) -> Any:
        """Execute the decorated async function."""
        return await self._func(**kwargs)


def extract_parameters(func: Callable) -> List[ToolParameter]:
    """Extract parameters from function signature.
    
    Args:
        func: Function to extract parameters from
        
    Returns:
        List of ToolParameter instances
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    parameters = []
    
    for param_name, param in sig.parameters.items():
        # Skip self/cls parameters
        if param_name in ('self', 'cls'):
            continue
        
        # Get type annotation
        param_type = type_hints.get(param_name, Any)
        tool_param_type = python_type_to_parameter_type(param_type)
        
        # Determine if required
        required = param.default is inspect.Parameter.empty
        
        # Extract description from docstring
        description = extract_param_description(func, param_name)
        
        # Create parameter
        tool_param = ToolParameter(
            name=param_name,
            type=tool_param_type,
            description=description,
            required=required,
            default=None if required else param.default
        )
        
        parameters.append(tool_param)
    
    return parameters


def extract_param_description(func: Callable, param_name: str) -> str:
    """Extract parameter description from docstring.
    
    Args:
        func: Function with docstring
        param_name: Parameter name to find description for
        
    Returns:
        Parameter description or default message
    """
    if not func.__doc__:
        return f"Parameter {param_name}"
    
    # Try to parse Google-style docstring
    lines = func.__doc__.strip().split('\n')
    in_args_section = False
    
    for i, line in enumerate(lines):
        # Check for Args section
        if line.strip() in ('Args:', 'Arguments:', 'Parameters:'):
            in_args_section = True
            continue
        
        # Exit on next section
        if in_args_section and line.strip().endswith(':') and line.strip() != ':':
            break
        
        # Look for parameter
        if in_args_section and param_name in line:
            # Extract description after parameter name
            if ':' in line:
                desc_start = line.find(':', line.find(param_name)) + 1
                description = line[desc_start:].strip()
                
                # Check for multiline description
                j = i + 1
                while j < len(lines) and lines[j].startswith('        '):
                    description += ' ' + lines[j].strip()
                    j += 1
                
                return description
    
    return f"Parameter {param_name}"


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
    author: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parameters: Optional[List[ToolParameter]] = None,
    deprecated: bool = False,
    deprecation_message: Optional[str] = None
) -> Callable:
    """Decorator to create a tool from a function.
    
    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to docstring)
        version: Tool version
        author: Tool author
        tags: Tool tags
        category: Tool category
        parameters: Explicit parameter definitions (auto-extracted if not provided)
        deprecated: Whether tool is deprecated
        deprecation_message: Deprecation message
        
    Returns:
        Decorator function
        
    Example:
        @tool(name="greet", description="Greet a person", tags=["utility"])
        def greet_person(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"
    """
    def decorator(func: Callable) -> Union[Tool, Callable]:
        # Determine tool name
        tool_name = name or func.__name__
        
        # Determine description
        tool_description = description or (func.__doc__ or "").strip().split('\n')[0]
        if not tool_description:
            tool_description = f"Tool {tool_name}"
        
        # Extract or use provided parameters
        tool_parameters = parameters or extract_parameters(func)
        
        # Create metadata
        metadata = ToolMetadata(
            name=tool_name,
            description=tool_description,
            version=version,
            author=author,
            tags=tags or [],
            category=category,
            deprecated=deprecated,
            deprecation_message=deprecation_message
        )
        
        # Create appropriate tool class
        if asyncio.iscoroutinefunction(func):
            tool_instance = DecoratedAsyncTool(func, metadata, tool_parameters)
        else:
            tool_instance = DecoratedTool(func, metadata, tool_parameters)
        
        # Add tool reference to function
        func.tool = tool_instance
        
        # Return wrapped function that returns tool
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If called with arguments, execute the tool
            if args or kwargs:
                return tool_instance.execute(**kwargs)
            # Otherwise return the tool instance
            return tool_instance
        
        wrapper.tool = tool_instance
        return wrapper
    
    return decorator


def async_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    version: str = "1.0.0",
    author: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parameters: Optional[List[ToolParameter]] = None
) -> Callable:
    """Decorator specifically for async tools.
    
    This is an alias for @tool that provides better IDE support
    and type hints for async functions.
    
    Args:
        Same as @tool decorator
        
    Example:
        @async_tool(name="fetch_data", tags=["network"])
        async def fetch_data(url: str) -> dict:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """
    return tool(
        name=name,
        description=description,
        version=version,
        author=author,
        tags=tags,
        category=category,
        parameters=parameters
    )


def param(
    name: str,
    type: Union[ToolParameterType, Type],
    description: str,
    required: bool = True,
    default: Any = None,
    constraints: Optional[Dict[str, Any]] = None
) -> ToolParameter:
    """Helper to create explicit parameter definitions.
    
    Args:
        name: Parameter name
        type: Parameter type (ToolParameterType or Python type)
        description: Parameter description
        required: Whether parameter is required
        default: Default value
        constraints: Additional constraints
        
    Returns:
        ToolParameter instance
        
    Example:
        @tool(parameters=[
            param("name", str, "Person's name"),
            param("age", int, "Person's age", constraints={"min": 0, "max": 150})
        ])
        def create_person(name: str, age: int) -> dict:
            return {"name": name, "age": age}
    """
    # Convert Python type to ToolParameterType if needed
    if not isinstance(type, ToolParameterType):
        type = python_type_to_parameter_type(type)
    
    return ToolParameter(
        name=name,
        type=type,
        description=description,
        required=required,
        default=default,
        constraints=constraints or {}
    )


def composite_tool(
    *tools: Union[Tool, Callable],
    name: str,
    description: str,
    version: str = "1.0.0",
    tags: Optional[List[str]] = None
) -> Tool:
    """Create a composite tool from multiple tools.
    
    Args:
        *tools: Tools to compose (Tool instances or decorated functions)
        name: Name for the composite tool
        description: Description of the composite tool
        version: Version of the composite tool
        tags: Tags for the composite tool
        
    Returns:
        CompositeTool instance
        
    Example:
        @tool
        def step1(input: str) -> dict:
            return {"processed": input.upper()}
        
        @tool
        def step2(processed: str) -> dict:
            return {"result": processed + "!"}
        
        pipeline = composite_tool(
            step1, step2,
            name="process_pipeline",
            description="Process input through two steps"
        )
    """
    from .base_refactored import CompositeTool
    
    # Convert decorated functions to tools
    tool_instances = []
    for t in tools:
        if hasattr(t, 'tool'):
            tool_instances.append(t.tool)
        elif isinstance(t, Tool):
            tool_instances.append(t)
        else:
            raise ToolError(f"Invalid tool type: {type(t)}")
    
    # Create composite
    composite = CompositeTool(
        tools=tool_instances,
        name=name,
        description=description
    )
    
    # Update metadata
    composite._metadata = ToolMetadata(
        name=name,
        description=description,
        version=version,
        tags=tags or ["composite"],
        category="composite"
    )
    
    return composite


def validate_result(
    validator: Callable[[Any], bool],
    error_message: str = "Result validation failed"
) -> Callable:
    """Decorator to add result validation to a tool.
    
    Args:
        validator: Function that returns True if result is valid
        error_message: Error message if validation fails
        
    Returns:
        Decorator function
        
    Example:
        @tool
        @validate_result(lambda x: x > 0, "Result must be positive")
        def calculate(value: int) -> int:
            return value * 2
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Handle ToolResult
            if isinstance(result, ToolResult):
                if result.success and not validator(result.data):
                    return ToolResult(
                        success=False,
                        error=error_message,
                        metadata=result.metadata
                    )
                return result
            
            # Handle raw result
            if not validator(result):
                raise ToolError(error_message)
            
            return result
        
        # Preserve tool attribute if present
        if hasattr(func, 'tool'):
            wrapper.tool = func.tool
        
        return wrapper
    
    return decorator