"""Tests for refactored base tool classes."""

import pytest
import asyncio
from datetime import datetime
from typing import Any, Dict

from src.tools.base_refactored import (
    Tool, AsyncTool, CompositeTool, ToolMetadata, ToolParameter,
    ToolParameterType, ToolResult
)
from src.exceptions import ToolError, ToolExecutionError, ToolValidationError


class TestToolResult:
    """Test ToolResult class."""
    
    def test_successful_result(self):
        """Test creating a successful result."""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            metadata={"tool": "test"},
            execution_time=1.5
        )
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata == {"tool": "test"}
        assert result.execution_time == 1.5
    
    def test_failed_result(self):
        """Test creating a failed result."""
        result = ToolResult(
            success=False,
            error="Something went wrong",
            metadata={"tool": "test"}
        )
        
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"
    
    def test_invalid_result_states(self):
        """Test that invalid result states raise errors."""
        # Success with error should fail
        with pytest.raises(ValueError, match="Successful result cannot have an error"):
            ToolResult(success=True, data="test", error="error")
        
        # Failure without error should fail
        with pytest.raises(ValueError, match="Failed result must have an error"):
            ToolResult(success=False, data=None)
    
    def test_unwrap_successful(self):
        """Test unwrapping successful result."""
        result = ToolResult(success=True, data="test_data")
        assert result.unwrap() == "test_data"
    
    def test_unwrap_failed(self):
        """Test unwrapping failed result raises exception."""
        result = ToolResult(
            success=False,
            error="Test error",
            metadata={"tool_name": "test_tool"}
        )
        
        with pytest.raises(ToolExecutionError) as exc_info:
            result.unwrap()
        
        assert exc_info.value.tool_name == "test_tool"
        assert "Test error" in str(exc_info.value)
    
    def test_map_successful(self):
        """Test mapping function over successful result."""
        result = ToolResult(success=True, data=5)
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.success is True
        assert mapped.data == 10
    
    def test_map_failed(self):
        """Test mapping over failed result returns same result."""
        result = ToolResult(success=False, error="Original error")
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.success is False
        assert mapped.error == "Original error"
        assert mapped.data is None
    
    def test_map_with_exception(self):
        """Test map handles exceptions in mapping function."""
        result = ToolResult(success=True, data=5)
        mapped = result.map(lambda x: x / 0)  # Division by zero
        
        assert mapped.success is False
        assert "division by zero" in mapped.error.lower()


class TestToolMetadata:
    """Test ToolMetadata class."""
    
    def test_minimal_metadata(self):
        """Test creating metadata with minimal fields."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool"
        )
        
        assert metadata.name == "test_tool"
        assert metadata.description == "A test tool"
        assert metadata.version == "1.0.0"  # Default
        assert metadata.deprecated is False  # Default
        assert metadata.tags == []  # Default
    
    def test_full_metadata(self):
        """Test creating metadata with all fields."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            version="2.0.0",
            author="Test Author",
            tags=["test", "example"],
            category="testing",
            deprecated=True,
            deprecation_message="Use new_tool instead"
        )
        
        assert metadata.name == "test_tool"
        assert metadata.version == "2.0.0"
        assert metadata.author == "Test Author"
        assert metadata.tags == ["test", "example"]
        assert metadata.category == "testing"
        assert metadata.deprecated is True
        assert metadata.deprecation_message == "Use new_tool instead"
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed in metadata."""
        metadata = ToolMetadata(
            name="test_tool",
            description="A test tool",
            custom_field="custom_value"
        )
        
        assert metadata.name == "test_tool"
        assert hasattr(metadata, 'custom_field')
        assert metadata.custom_field == "custom_value"


class TestToolParameter:
    """Test ToolParameter class."""
    
    def test_required_parameter(self):
        """Test creating a required parameter."""
        param = ToolParameter(
            name="input_text",
            type=ToolParameterType.STRING,
            description="Input text to process",
            required=True
        )
        
        assert param.name == "input_text"
        assert param.type == ToolParameterType.STRING
        assert param.required is True
        assert param.default is None
    
    def test_optional_parameter_with_default(self):
        """Test creating an optional parameter with default."""
        param = ToolParameter(
            name="count",
            type=ToolParameterType.INTEGER,
            description="Number of items",
            required=False,
            default=10
        )
        
        assert param.name == "count"
        assert param.type == ToolParameterType.INTEGER
        assert param.required is False
        assert param.default == 10
    
    def test_parameter_with_constraints(self):
        """Test parameter with constraints."""
        param = ToolParameter(
            name="age",
            type=ToolParameterType.INTEGER,
            description="Person's age",
            constraints={"min": 0, "max": 150}
        )
        
        assert param.constraints == {"min": 0, "max": 150}
    
    def test_invalid_parameter_name(self):
        """Test that invalid parameter names are rejected."""
        with pytest.raises(ValueError, match="must be a valid Python identifier"):
            ToolParameter(
                name="invalid-name",  # Hyphens not allowed
                type=ToolParameterType.STRING,
                description="Test"
            )
    
    def test_default_type_validation(self):
        """Test that default values must match parameter type."""
        # Valid default
        param = ToolParameter(
            name="test",
            type=ToolParameterType.INTEGER,
            description="Test",
            default=42
        )
        assert param.default == 42
        
        # Invalid default type
        with pytest.raises(ValueError, match="doesn't match parameter type"):
            ToolParameter(
                name="test",
                type=ToolParameterType.INTEGER,
                description="Test",
                default="not_an_integer"
            )


class SimpleTool(Tool):
    """Simple test tool implementation."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="simple_tool",
            description="A simple test tool",
            tags=["test"]
        )
    
    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="text",
                type=ToolParameterType.STRING,
                description="Text to process",
                required=True
            ),
            ToolParameter(
                name="repeat",
                type=ToolParameterType.INTEGER,
                description="Number of repetitions",
                required=False,
                default=1
            )
        ]
    
    def _execute_impl(self, **kwargs) -> dict:
        text = kwargs["text"]
        repeat = kwargs.get("repeat", 1)
        return {"result": text * repeat}


class TestTool:
    """Test Tool base class."""
    
    def test_tool_properties(self):
        """Test tool property accessors."""
        tool = SimpleTool()
        
        assert tool.name == "simple_tool"
        assert tool.description == "A simple test tool"
        assert len(tool.parameters) == 2
    
    def test_tool_execution_success(self):
        """Test successful tool execution."""
        tool = SimpleTool()
        result = tool.execute(text="hello", repeat=3)
        
        assert result.success is True
        assert result.data == {"result": "hellohellohello"}
        assert result.error is None
        assert result.execution_time > 0
        assert result.metadata["tool_name"] == "simple_tool"
    
    def test_tool_execution_with_defaults(self):
        """Test execution with default parameters."""
        tool = SimpleTool()
        result = tool.execute(text="hello")
        
        assert result.success is True
        assert result.data == {"result": "hello"}
    
    def test_tool_validation_missing_required(self):
        """Test that missing required parameters raise error."""
        tool = SimpleTool()
        
        with pytest.raises(ToolValidationError) as exc_info:
            tool.execute(repeat=2)  # Missing required 'text' parameter
        
        assert "text" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()
    
    def test_tool_validation_unknown_parameter(self):
        """Test that unknown parameters raise error."""
        tool = SimpleTool()
        
        with pytest.raises(ToolValidationError) as exc_info:
            tool.execute(text="hello", unknown_param="value")
        
        assert "unknown_param" in str(exc_info.value).lower()
    
    def test_tool_validation_wrong_type(self):
        """Test that wrong parameter types raise error."""
        tool = SimpleTool()
        
        with pytest.raises(ToolValidationError) as exc_info:
            tool.execute(text="hello", repeat="not_a_number")
        
        assert "repeat" in str(exc_info.value)
    
    def test_tool_statistics(self):
        """Test tool execution statistics."""
        tool = SimpleTool()
        
        # Initial stats
        stats = tool.get_statistics()
        assert stats["execution_count"] == 0
        assert stats["total_execution_time"] == 0
        assert stats["average_execution_time"] == 0
        assert stats["last_execution"] is None
        
        # Execute tool
        tool.execute(text="test")
        
        # Check updated stats
        stats = tool.get_statistics()
        assert stats["execution_count"] == 1
        assert stats["total_execution_time"] > 0
        assert stats["average_execution_time"] > 0
        assert stats["last_execution"] is not None
    
    def test_tool_to_dict(self):
        """Test converting tool to dictionary."""
        tool = SimpleTool()
        tool_dict = tool.to_dict()
        
        assert "metadata" in tool_dict
        assert "parameters" in tool_dict
        assert "statistics" in tool_dict
        assert tool_dict["metadata"]["name"] == "simple_tool"
        assert len(tool_dict["parameters"]) == 2


class SimpleAsyncTool(AsyncTool):
    """Simple async test tool."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="async_tool",
            description="An async test tool"
        )
    
    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="delay",
                type=ToolParameterType.FLOAT,
                description="Delay in seconds",
                required=False,
                default=0.1
            )
        ]
    
    async def _execute_impl_async(self, **kwargs) -> dict:
        delay = kwargs.get("delay", 0.1)
        await asyncio.sleep(delay)
        return {"completed": True, "delay": delay}


class TestAsyncTool:
    """Test AsyncTool class."""
    
    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test async tool execution."""
        tool = SimpleAsyncTool()
        result = await tool.execute_async(delay=0.05)
        
        assert result.success is True
        assert result.data == {"completed": True, "delay": 0.05}
        assert result.execution_time >= 0.05
    
    def test_async_tool_sync_execution(self):
        """Test that async tools can be executed synchronously."""
        tool = SimpleAsyncTool()
        result = tool.execute(delay=0.05)
        
        assert result.success is True
        assert result.data == {"completed": True, "delay": 0.05}


class TestCompositeTool:
    """Test CompositeTool class."""
    
    def test_composite_tool_creation(self):
        """Test creating a composite tool."""
        tool1 = SimpleTool()
        tool2 = SimpleTool()
        
        composite = CompositeTool(
            tools=[tool1, tool2],
            name="composite_test",
            description="A composite tool for testing"
        )
        
        assert composite.name == "composite_test"
        assert composite.description == "A composite tool for testing"
        assert "composite" in composite.metadata.tags
    
    def test_composite_tool_parameters(self):
        """Test that composite tool combines parameters."""
        tool1 = SimpleTool()
        tool2 = SimpleTool()  # Same parameters
        
        composite = CompositeTool(
            tools=[tool1, tool2],
            name="composite_test",
            description="Test composite"
        )
        
        # Should have unique parameters only
        params = composite.parameters
        param_names = [p.name for p in params]
        assert len(param_names) == len(set(param_names))  # No duplicates
    
    def test_composite_tool_execution(self):
        """Test executing a composite tool."""
        tool1 = SimpleTool()
        tool2 = SimpleTool()
        
        composite = CompositeTool(
            tools=[tool1, tool2],
            name="composite_test",
            description="Test composite"
        )
        
        result = composite.execute(text="hello", repeat=2)
        
        assert result.success is True
        assert result.data["steps"] == 2
        assert len(result.data["results"]) == 2
        assert result.data["final_output"] == {"result": "hellohello"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])