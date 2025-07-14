"""Decorators for creating tools."""

import functools
import inspect
from typing import Callable, List, Optional, Any, Dict, Union
import asyncio

from .base import Tool, AsyncTool, ToolParameter, ToolResult, ToolParameterType
from .registry import tool_registry


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    version: str = "1.0.0",
    author: str = "Ajentik",
    requires_confirmation: bool = False,
    is_safe: bool = True,
    register: bool = True,
    aliases: Optional[List[str]] = None
):
    """Decorator to convert a function into a Tool.
    
    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        category: Tool category for organization
        version: Tool version
        author: Tool author
        requires_confirmation: Whether tool requires user confirmation
        is_safe: Whether tool is safe to execute without restrictions
        register: Whether to automatically register the tool
        aliases: Alternative names for the tool
    
    Example:
        @tool(category="file_system", requires_confirmation=True)
        def delete_file(path: str) -> bool:
            '''Delete a file at the given path.'''
            os.remove(path)
            return True
    """
    def decorator(func: Callable) -> Tool:
        # Extract function metadata
        func_name = name or func.__name__
        func_description = description or (func.__doc__ or "").strip().split('\n')[0]
        
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            # Skip self/cls parameters
            if param_name in ['self', 'cls']:
                continue
            
            # Determine parameter type from annotation or default
            param_type = ToolParameterType.STRING  # default
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                # Map Python types to ToolParameterType
                if annotation == str:
                    param_type = ToolParameterType.STRING
                elif annotation == int:
                    param_type = ToolParameterType.INTEGER
                elif annotation == float:
                    param_type = ToolParameterType.FLOAT
                elif annotation == bool:
                    param_type = ToolParameterType.BOOLEAN
                elif annotation == list or str(annotation).startswith('List'):
                    param_type = ToolParameterType.ARRAY
                elif annotation == dict or str(annotation).startswith('Dict'):
                    param_type = ToolParameterType.OBJECT
            
            # Check if parameter is required
            required = param.default == inspect.Parameter.empty
            default_value = None if required else param.default
            
            # Extract parameter description from docstring if available
            param_description = f"Parameter {param_name}"
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=param_description,
                required=required,
                default=default_value
            ))
        
        # Create tool class
        class DecoratedTool(Tool):
            @property
            def name(self) -> str:
                return func_name
            
            @property
            def description(self) -> str:
                return func_description
            
            @property
            def category(self) -> str:
                return category
            
            @property
            def version(self) -> str:
                return version
            
            @property
            def author(self) -> str:
                return author
            
            @property
            def requires_confirmation(self) -> bool:
                return requires_confirmation
            
            @property
            def is_safe(self) -> bool:
                return is_safe
            
            def parameters(self) -> List[ToolParameter]:
                return parameters
            
            def execute(self, **kwargs) -> ToolResult:
                try:
                    result = func(**kwargs)
                    
                    # Convert result to ToolResult if needed
                    if isinstance(result, ToolResult):
                        return result
                    else:
                        return ToolResult(
                            success=True,
                            data=result
                        )
                except Exception as e:
                    return ToolResult(
                        success=False,
                        error=str(e),
                        metadata={"error_type": type(e).__name__}
                    )
        
        # Create instance
        tool_instance = DecoratedTool()
        
        # Register if requested
        if register:
            tool_registry.register(tool_instance, aliases=aliases)
        
        # Attach the tool instance to the function for access
        func._tool = tool_instance
        
        # Return a wrapper that allows both function and tool usage
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if args:
                # Called as regular function
                return func(*args, **kwargs)
            else:
                # Called as tool
                return tool_instance(**kwargs)
        
        wrapper.tool = tool_instance
        return wrapper
    
    return decorator


def async_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: str = "general",
    version: str = "1.0.0",
    author: str = "Ajentik",
    requires_confirmation: bool = False,
    is_safe: bool = True,
    register: bool = True,
    aliases: Optional[List[str]] = None
):
    """Decorator to convert an async function into an AsyncTool.
    
    Similar to @tool but for async functions.
    
    Example:
        @async_tool(category="network")
        async def fetch_url(url: str) -> str:
            '''Fetch content from a URL.'''
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()
    """
    def decorator(func: Callable) -> AsyncTool:
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f"Function {func.__name__} must be async")
        
        # Extract function metadata
        func_name = name or func.__name__
        func_description = description or (func.__doc__ or "").strip().split('\n')[0]
        
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            # Skip self/cls parameters
            if param_name in ['self', 'cls']:
                continue
            
            # Determine parameter type from annotation or default
            param_type = ToolParameterType.STRING  # default
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                # Map Python types to ToolParameterType
                if annotation == str:
                    param_type = ToolParameterType.STRING
                elif annotation == int:
                    param_type = ToolParameterType.INTEGER
                elif annotation == float:
                    param_type = ToolParameterType.FLOAT
                elif annotation == bool:
                    param_type = ToolParameterType.BOOLEAN
                elif annotation == list or str(annotation).startswith('List'):
                    param_type = ToolParameterType.ARRAY
                elif annotation == dict or str(annotation).startswith('Dict'):
                    param_type = ToolParameterType.OBJECT
            
            # Check if parameter is required
            required = param.default == inspect.Parameter.empty
            default_value = None if required else param.default
            
            # Extract parameter description from docstring if available
            param_description = f"Parameter {param_name}"
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=param_description,
                required=required,
                default=default_value
            ))
        
        # Create async tool class
        class DecoratedAsyncTool(AsyncTool):
            @property
            def name(self) -> str:
                return func_name
            
            @property
            def description(self) -> str:
                return func_description
            
            @property
            def category(self) -> str:
                return category
            
            @property
            def version(self) -> str:
                return version
            
            @property
            def author(self) -> str:
                return author
            
            @property
            def requires_confirmation(self) -> bool:
                return requires_confirmation
            
            @property
            def is_safe(self) -> bool:
                return is_safe
            
            def parameters(self) -> List[ToolParameter]:
                return parameters
            
            async def execute(self, **kwargs) -> ToolResult:
                try:
                    result = await func(**kwargs)
                    
                    # Convert result to ToolResult if needed
                    if isinstance(result, ToolResult):
                        return result
                    else:
                        return ToolResult(
                            success=True,
                            data=result
                        )
                except Exception as e:
                    return ToolResult(
                        success=False,
                        error=str(e),
                        metadata={"error_type": type(e).__name__}
                    )
        
        # Create instance
        tool_instance = DecoratedAsyncTool()
        
        # Register if requested
        if register:
            tool_registry.register(tool_instance, aliases=aliases)
        
        # Attach the tool instance to the function for access
        func._tool = tool_instance
        
        # Return a wrapper that allows both function and tool usage
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if args:
                # Called as regular function
                return await func(*args, **kwargs)
            else:
                # Called as tool - need to handle sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context
                    result = await tool_instance.execute(**kwargs)
                else:
                    # Sync context - run in event loop
                    result = asyncio.run(tool_instance.execute(**kwargs))
                return result
        
        wrapper.tool = tool_instance
        return wrapper
    
    return decorator


def parameter(
    name: str,
    param_type: Union[ToolParameterType, str],
    description: str,
    required: bool = True,
    default: Any = None,
    constraints: Optional[Dict[str, Any]] = None
):
    """Decorator to add parameter metadata to a function.
    
    This is useful when you want more control over parameter definitions.
    
    Example:
        @tool()
        @parameter("path", ToolParameterType.FILE_PATH, "Path to the file", required=True)
        @parameter("encoding", ToolParameterType.STRING, "File encoding", default="utf-8")
        def read_file(path: str, encoding: str = "utf-8") -> str:
            with open(path, 'r', encoding=encoding) as f:
                return f.read()
    """
    def decorator(func):
        # Store parameter metadata on the function
        if not hasattr(func, '_tool_parameters'):
            func._tool_parameters = []
        
        func._tool_parameters.append(ToolParameter(
            name=name,
            type=param_type if isinstance(param_type, ToolParameterType) else ToolParameterType(param_type),
            description=description,
            required=required,
            default=default,
            constraints=constraints
        ))
        
        return func
    
    return decorator