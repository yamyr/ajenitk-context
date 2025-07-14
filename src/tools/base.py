"""Base classes for the tool system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Type
from enum import Enum
from datetime import datetime
import inspect
import asyncio

from pydantic import BaseModel, Field, validator


class ToolParameterType(str, Enum):
    """Supported parameter types for tools."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    FILE_PATH = "file_path"
    URL = "url"


class ToolParameter(BaseModel):
    """Definition of a tool parameter."""
    name: str = Field(..., description="Parameter name")
    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(True, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Additional constraints")
    
    @validator('default')
    def validate_default(cls, v, values):
        """Ensure default value matches the parameter type."""
        if v is None:
            return v
            
        param_type = values.get('type')
        if param_type == ToolParameterType.STRING and not isinstance(v, str):
            raise ValueError(f"Default value must be string for type {param_type}")
        elif param_type == ToolParameterType.INTEGER and not isinstance(v, int):
            raise ValueError(f"Default value must be integer for type {param_type}")
        elif param_type == ToolParameterType.FLOAT and not isinstance(v, (int, float)):
            raise ValueError(f"Default value must be float for type {param_type}")
        elif param_type == ToolParameterType.BOOLEAN and not isinstance(v, bool):
            raise ValueError(f"Default value must be boolean for type {param_type}")
            
        return v


class ToolResult(BaseModel):
    """Result from tool execution."""
    success: bool = Field(..., description="Whether execution was successful")
    data: Optional[Any] = Field(None, description="Result data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution timestamp")


class ToolError(Exception):
    """Base exception for tool errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class Tool(ABC):
    """Abstract base class for all tools."""
    
    def __init__(self):
        self._validate_implementation()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for the tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass
    
    @property
    def category(self) -> str:
        """Category for organizing tools."""
        return "general"
    
    @property
    def version(self) -> str:
        """Tool version."""
        return "1.0.0"
    
    @property
    def author(self) -> str:
        """Tool author."""
        return "Ajentik"
    
    @property
    def requires_confirmation(self) -> bool:
        """Whether tool requires user confirmation before execution."""
        return False
    
    @property
    def is_safe(self) -> bool:
        """Whether tool is safe to execute without restrictions."""
        return True
    
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Define the parameters this tool accepts."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and normalize input parameters."""
        params = {p.name: p for p in self.parameters()}
        validated = {}
        
        # Check for unknown parameters
        unknown = set(kwargs.keys()) - set(params.keys())
        if unknown:
            raise ToolError(f"Unknown parameters: {', '.join(unknown)}")
        
        # Validate each parameter
        for param_name, param_def in params.items():
            if param_name in kwargs:
                value = kwargs[param_name]
                # Type validation would go here
                validated[param_name] = value
            elif param_def.required:
                if param_def.default is not None:
                    validated[param_name] = param_def.default
                else:
                    raise ToolError(f"Required parameter '{param_name}' not provided")
            elif param_def.default is not None:
                validated[param_name] = param_def.default
        
        return validated
    
    def _validate_implementation(self):
        """Validate that the tool is properly implemented."""
        # Check that execute method is not async in base Tool
        if inspect.iscoroutinefunction(self.execute):
            raise TypeError(
                f"Tool '{self.__class__.__name__}' has async execute method. "
                "Use AsyncTool base class for async tools."
            )
    
    def __call__(self, **kwargs) -> ToolResult:
        """Allow tool to be called directly."""
        import time
        start_time = time.time()
        
        try:
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Execute tool
            result = self.execute(**validated_params)
            
            # Add execution time
            result.execution_time = time.time() - start_time
            
            return result
            
        except ToolError:
            raise
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"error_type": type(e).__name__},
                execution_time=time.time() - start_time
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for the tool."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "author": self.author,
            "requires_confirmation": self.requires_confirmation,
            "is_safe": self.is_safe,
            "parameters": [p.dict() for p in self.parameters()]
        }
    
    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"
    
    def __repr__(self) -> str:
        return f"<Tool: {self.name} [{self.category}]>"


class AsyncTool(Tool):
    """Base class for asynchronous tools."""
    
    def _validate_implementation(self):
        """Validate that the tool is properly implemented."""
        # Check that execute method is async
        if not inspect.iscoroutinefunction(self.execute):
            raise TypeError(
                f"AsyncTool '{self.__class__.__name__}' must have async execute method"
            )
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool asynchronously."""
        pass
    
    def __call__(self, **kwargs) -> ToolResult:
        """Allow async tool to be called directly."""
        import time
        start_time = time.time()
        
        try:
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Execute tool (handle async)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                future = asyncio.create_task(self.execute(**validated_params))
                result = loop.run_until_complete(future)
            else:
                # Otherwise, run in a new event loop
                result = asyncio.run(self.execute(**validated_params))
            
            # Add execution time
            result.execution_time = time.time() - start_time
            
            return result
            
        except ToolError:
            raise
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"error_type": type(e).__name__},
                execution_time=time.time() - start_time
            )


class CompositeTool(Tool):
    """Base class for tools that compose multiple other tools."""
    
    def __init__(self, tools: List[Tool]):
        self.tools = tools
        super().__init__()
    
    @property
    def sub_tools(self) -> List[Tool]:
        """Get list of composed tools."""
        return self.tools
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a specific sub-tool."""
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            raise ToolError(f"Sub-tool '{tool_name}' not found")
        return tool(**kwargs)