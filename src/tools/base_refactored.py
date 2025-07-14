"""Refactored base classes for the tool system.

This module provides the core abstractions for the Ajentik tool system,
with improved separation of concerns, type safety, and error handling.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Type, Generic, TypeVar, Protocol
from enum import Enum
from datetime import datetime
import inspect
import asyncio
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, validator

from ..exceptions import ToolError, ToolExecutionError, ToolValidationError
from ..utils.validation import validate_parameters
from ..utils.type_mapping import python_type_to_parameter_type
from ..utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


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
    """Definition of a tool parameter with enhanced validation."""
    name: str = Field(..., description="Parameter name")
    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(True, description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    constraints: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Additional constraints (min, max, pattern, etc.)"
    )
    
    @validator('default')
    def validate_default(cls, v, values):
        """Ensure default value matches the parameter type."""
        if v is None:
            return v
            
        from ..utils.type_mapping import validate_type_match
        param_type = values.get('type')
        
        if not validate_type_match(v, param_type):
            raise ValueError(
                f"Default value {v} doesn't match parameter type {param_type}"
            )
            
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Ensure parameter name is valid Python identifier."""
        if not v.isidentifier():
            raise ValueError(f"Parameter name '{v}' must be a valid Python identifier")
        return v
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        extra = "forbid"


@dataclass
class ToolResult(Generic[T]):
    """Result of tool execution with generic type support."""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None
    
    def __post_init__(self):
        """Validate result state."""
        if self.success and self.error:
            raise ValueError("Successful result cannot have an error")
        if not self.success and not self.error:
            raise ValueError("Failed result must have an error message")
    
    def unwrap(self) -> T:
        """Get data or raise exception if failed.
        
        Returns:
            The result data
            
        Raises:
            ToolExecutionError: If the result represents a failure
        """
        if not self.success:
            raise ToolExecutionError(
                tool_name=self.metadata.get('tool_name', 'unknown'),
                message=self.error or "Tool execution failed"
            )
        return self.data
    
    def map(self, func: callable) -> 'ToolResult':
        """Map function over successful result."""
        if self.success and self.data is not None:
            try:
                new_data = func(self.data)
                return ToolResult(
                    success=True,
                    data=new_data,
                    metadata=self.metadata,
                    execution_time=self.execution_time
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=str(e),
                    metadata=self.metadata,
                    execution_time=self.execution_time
                )
        return self


class ToolMetadata(BaseModel):
    """Metadata about a tool."""
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"


class ToolProtocol(Protocol):
    """Protocol defining the tool interface."""
    
    @property
    def metadata(self) -> ToolMetadata:
        """Tool metadata."""
        ...
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters."""
        ...
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        ...


class Tool(ABC):
    """Abstract base class for all tools with improved design."""
    
    def __init__(self):
        """Initialize tool with metadata validation."""
        self._execution_count = 0
        self._total_execution_time = 0.0
        self._last_execution = None
        self._validate_metadata()
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Tool metadata.
        
        Returns:
            ToolMetadata instance describing the tool
        """
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameter definitions.
        
        Returns:
            List of ToolParameter instances
        """
        pass
    
    @property
    def name(self) -> str:
        """Tool name (convenience property)."""
        return self.metadata.name
    
    @property
    def description(self) -> str:
        """Tool description (convenience property)."""
        return self.metadata.description
    
    def _validate_metadata(self) -> None:
        """Validate tool metadata on initialization."""
        try:
            metadata = self.metadata
            if not metadata.name:
                raise ToolError("Tool name cannot be empty")
            if not metadata.description:
                raise ToolError("Tool description cannot be empty")
        except Exception as e:
            raise ToolError(f"Invalid tool metadata: {str(e)}")
    
    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate and normalize input parameters.
        
        Args:
            **kwargs: Raw parameter values
            
        Returns:
            Validated and normalized parameters
            
        Raises:
            ToolValidationError: If validation fails
        """
        return validate_parameters(kwargs, self.parameters)
    
    @abstractmethod
    def _execute_impl(self, **kwargs) -> Any:
        """Internal execution implementation.
        
        Args:
            **kwargs: Validated parameters
            
        Returns:
            Execution result (will be wrapped in ToolResult)
        """
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with validation and error handling.
        
        Args:
            **kwargs: Parameter values
            
        Returns:
            ToolResult instance
        """
        start_time = datetime.utcnow()
        metadata = {
            'tool_name': self.name,
            'parameters': kwargs,
            'timestamp': start_time.isoformat()
        }
        
        try:
            # Check if deprecated
            if self.metadata.deprecated:
                logger.warning(
                    f"Tool '{self.name}' is deprecated: {self.metadata.deprecation_message}"
                )
            
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Execute tool
            result = self._execute_impl(**validated_params)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update statistics
            self._execution_count += 1
            self._total_execution_time += execution_time
            self._last_execution = datetime.utcnow()
            
            # Return success result
            return ToolResult(
                success=True,
                data=result,
                metadata=metadata,
                execution_time=execution_time
            )
            
        except ToolError:
            # Re-raise tool errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Tool '{self.name}' execution failed: {str(e)}")
            
            return ToolResult(
                success=False,
                error=str(e),
                metadata={**metadata, 'error_type': type(e).__name__},
                execution_time=execution_time
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tool execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        avg_time = (
            self._total_execution_time / self._execution_count
            if self._execution_count > 0 else 0
        )
        
        return {
            'execution_count': self._execution_count,
            'total_execution_time': self._total_execution_time,
            'average_execution_time': avg_time,
            'last_execution': self._last_execution.isoformat() if self._last_execution else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation.
        
        Returns:
            Dictionary with tool information
        """
        return {
            'metadata': self.metadata.dict(),
            'parameters': [p.dict() for p in self.parameters],
            'statistics': self.get_statistics()
        }


class AsyncTool(Tool):
    """Base class for asynchronous tools."""
    
    @abstractmethod
    async def _execute_impl_async(self, **kwargs) -> Any:
        """Async execution implementation.
        
        Args:
            **kwargs: Validated parameters
            
        Returns:
            Execution result
        """
        pass
    
    def _execute_impl(self, **kwargs) -> Any:
        """Sync wrapper for async execution."""
        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async method
        if loop.is_running():
            # If loop is already running, schedule coroutine
            future = asyncio.ensure_future(self._execute_impl_async(**kwargs))
            return future
        else:
            # If loop is not running, run until complete
            return loop.run_until_complete(self._execute_impl_async(**kwargs))
    
    async def execute_async(self, **kwargs) -> ToolResult:
        """Execute tool asynchronously.
        
        Args:
            **kwargs: Parameter values
            
        Returns:
            ToolResult instance
        """
        start_time = datetime.utcnow()
        metadata = {
            'tool_name': self.name,
            'parameters': kwargs,
            'timestamp': start_time.isoformat()
        }
        
        try:
            # Validate parameters
            validated_params = self.validate_parameters(**kwargs)
            
            # Execute tool
            result = await self._execute_impl_async(**validated_params)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Update statistics
            self._execution_count += 1
            self._total_execution_time += execution_time
            self._last_execution = datetime.utcnow()
            
            return ToolResult(
                success=True,
                data=result,
                metadata=metadata,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Async tool '{self.name}' execution failed: {str(e)}")
            
            return ToolResult(
                success=False,
                error=str(e),
                metadata={**metadata, 'error_type': type(e).__name__},
                execution_time=execution_time
            )


class CompositeTool(Tool):
    """Tool that combines multiple tools into a pipeline."""
    
    def __init__(self, tools: List[Tool], name: str, description: str):
        """Initialize composite tool.
        
        Args:
            tools: List of tools to execute in sequence
            name: Name for the composite tool
            description: Description of what the composite does
        """
        self._tools = tools
        self._name = name
        self._description = description
        super().__init__()
    
    @property
    def metadata(self) -> ToolMetadata:
        """Composite tool metadata."""
        return ToolMetadata(
            name=self._name,
            description=self._description,
            tags=["composite"],
            category="composite"
        )
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """Combined parameters from all tools."""
        # Collect unique parameters from all tools
        param_map = {}
        for tool in self._tools:
            for param in tool.parameters:
                if param.name not in param_map:
                    param_map[param.name] = param
        
        return list(param_map.values())
    
    def _execute_impl(self, **kwargs) -> Any:
        """Execute tools in sequence."""
        results = []
        current_data = kwargs
        
        for i, tool in enumerate(self._tools):
            # Filter parameters for current tool
            tool_params = {
                p.name: current_data.get(p.name)
                for p in tool.parameters
                if p.name in current_data
            }
            
            # Execute tool
            result = tool.execute(**tool_params)
            
            if not result.success:
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"Step {i+1} ({tool.name}) failed: {result.error}"
                )
            
            results.append(result)
            
            # Use result as input for next tool
            if isinstance(result.data, dict):
                current_data.update(result.data)
        
        return {
            'steps': len(self._tools),
            'results': [r.data for r in results],
            'final_output': results[-1].data if results else None
        }