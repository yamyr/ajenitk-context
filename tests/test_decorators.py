"""Tests for refactored tool decorators."""

import pytest
import asyncio
from typing import List, Optional

from src.tools.decorators_refactored import (
    tool, async_tool, param, composite_tool, validate_result,
    extract_parameters, extract_param_description,
    DecoratedTool, DecoratedAsyncTool
)
from src.tools.base_refactored import (
    Tool, ToolParameter, ToolParameterType, ToolResult, ToolMetadata
)
from src.exceptions import ToolError


class TestExtractParameters:
    """Test parameter extraction from functions."""
    
    def test_extract_simple_parameters(self):
        """Test extracting simple parameters."""
        def func(name: str, age: int, active: bool = True):
            pass
        
        params = extract_parameters(func)
        
        assert len(params) == 3
        
        # Check name parameter
        assert params[0].name == "name"
        assert params[0].type == ToolParameterType.STRING
        assert params[0].required is True
        
        # Check age parameter
        assert params[1].name == "age"
        assert params[1].type == ToolParameterType.INTEGER
        assert params[1].required is True
        
        # Check active parameter
        assert params[2].name == "active"
        assert params[2].type == ToolParameterType.BOOLEAN
        assert params[2].required is False
        assert params[2].default is True
    
    def test_extract_complex_types(self):
        """Test extracting complex type parameters."""
        def func(items: List[str], config: dict, data: Optional[dict] = None):
            pass
        
        params = extract_parameters(func)
        
        assert params[0].type == ToolParameterType.ARRAY
        assert params[1].type == ToolParameterType.OBJECT
        assert params[2].type == ToolParameterType.OBJECT
        assert params[2].required is False
    
    def test_skip_self_parameter(self):
        """Test that self parameter is skipped."""
        class TestClass:
            def method(self, value: str):
                pass
        
        params = extract_parameters(TestClass.method)
        
        assert len(params) == 1
        assert params[0].name == "value"


class TestExtractParamDescription:
    """Test parameter description extraction."""
    
    def test_extract_google_style_docstring(self):
        """Test extracting from Google-style docstring."""
        def func(name: str, age: int):
            """Test function.
            
            Args:
                name: The person's name
                age: The person's age in years
            """
            pass
        
        desc1 = extract_param_description(func, "name")
        desc2 = extract_param_description(func, "age")
        
        assert desc1 == "The person's name"
        assert desc2 == "The person's age in years"
    
    def test_extract_multiline_description(self):
        """Test extracting multiline descriptions."""
        def func(config: dict):
            """Test function.
            
            Args:
                config: Configuration dictionary containing
                    multiple settings and options
            """
            pass
        
        desc = extract_param_description(func, "config")
        assert "Configuration dictionary" in desc
        assert "multiple settings" in desc
    
    def test_no_docstring(self):
        """Test default description when no docstring."""
        def func(value: str):
            pass
        
        desc = extract_param_description(func, "value")
        assert desc == "Parameter value"


class TestToolDecorator:
    """Test @tool decorator."""
    
    def test_simple_tool_decoration(self):
        """Test decorating a simple function."""
        @tool(name="greet", description="Greet someone")
        def greet(name: str) -> str:
            return f"Hello, {name}!"
        
        # Check tool instance
        assert hasattr(greet, 'tool')
        tool_instance = greet.tool
        
        assert isinstance(tool_instance, Tool)
        assert tool_instance.name == "greet"
        assert tool_instance.description == "Greet someone"
        assert len(tool_instance.parameters) == 1
        assert tool_instance.parameters[0].name == "name"
    
    def test_tool_with_defaults(self):
        """Test tool with default parameter values."""
        @tool
        def process(text: str, uppercase: bool = False) -> str:
            """Process text with optional uppercase."""
            return text.upper() if uppercase else text
        
        tool_instance = process.tool
        
        # Name should default to function name
        assert tool_instance.name == "process"
        # Description should come from docstring
        assert "Process text" in tool_instance.description
        
        # Check parameters
        assert len(tool_instance.parameters) == 2
        assert tool_instance.parameters[1].required is False
        assert tool_instance.parameters[1].default is False
    
    def test_tool_execution(self):
        """Test executing a decorated tool."""
        @tool(tags=["test"])
        def add(a: int, b: int) -> int:
            return a + b
        
        # Execute via tool instance
        result = add.tool.execute(a=5, b=3)
        assert result.success is True
        assert result.data == 8
        
        # Execute via decorated function
        result2 = add(a=10, b=20)
        assert result2.success is True
        assert result2.data == 30
    
    def test_tool_with_metadata(self):
        """Test tool with full metadata."""
        @tool(
            name="advanced_tool",
            description="An advanced tool",
            version="2.0.0",
            author="Test Author",
            tags=["advanced", "test"],
            category="utilities",
            deprecated=True,
            deprecation_message="Use new_tool instead"
        )
        def advanced():
            return "result"
        
        metadata = advanced.tool.metadata
        
        assert metadata.name == "advanced_tool"
        assert metadata.version == "2.0.0"
        assert metadata.author == "Test Author"
        assert metadata.tags == ["advanced", "test"]
        assert metadata.category == "utilities"
        assert metadata.deprecated is True
        assert metadata.deprecation_message == "Use new_tool instead"
    
    def test_tool_with_explicit_parameters(self):
        """Test tool with explicitly defined parameters."""
        @tool(
            parameters=[
                param("text", str, "Text to process"),
                param("count", int, "Number of times", required=False, default=1)
            ]
        )
        def repeat(text: str, count: int = 1) -> str:
            return text * count
        
        params = repeat.tool.parameters
        
        assert len(params) == 2
        assert params[0].description == "Text to process"
        assert params[1].description == "Number of times"
        assert params[1].default == 1


class TestAsyncToolDecorator:
    """Test @async_tool decorator."""
    
    def test_async_tool_decoration(self):
        """Test decorating an async function."""
        @async_tool(name="fetch", tags=["async", "network"])
        async def fetch_data(url: str) -> dict:
            """Fetch data from URL."""
            await asyncio.sleep(0.01)
            return {"url": url, "data": "mock"}
        
        tool_instance = fetch_data.tool
        
        assert isinstance(tool_instance, DecoratedAsyncTool)
        assert tool_instance.name == "fetch"
        assert "async" in tool_instance.metadata.tags
    
    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """Test executing an async tool."""
        @async_tool
        async def async_process(value: int) -> int:
            await asyncio.sleep(0.01)
            return value * 2
        
        # Execute async
        result = await async_process.tool.execute_async(value=5)
        assert result.success is True
        assert result.data == 10
        
        # Also test sync execution
        result2 = async_process.tool.execute(value=3)
        assert result2.success is True
        assert result2.data == 6


class TestParamHelper:
    """Test param() helper function."""
    
    def test_param_creation(self):
        """Test creating parameters with param()."""
        p1 = param("name", str, "Person's name")
        p2 = param("age", int, "Person's age", required=False, default=0)
        p3 = param("score", ToolParameterType.FLOAT, "Test score",
                  constraints={"min": 0, "max": 100})
        
        assert p1.name == "name"
        assert p1.type == ToolParameterType.STRING
        assert p1.required is True
        
        assert p2.name == "age"
        assert p2.type == ToolParameterType.INTEGER
        assert p2.required is False
        assert p2.default == 0
        
        assert p3.type == ToolParameterType.FLOAT
        assert p3.constraints == {"min": 0, "max": 100}


class TestCompositeTool:
    """Test composite_tool() function."""
    
    def test_create_composite(self):
        """Test creating a composite tool."""
        @tool
        def step1(text: str) -> dict:
            return {"processed": text.upper()}
        
        @tool
        def step2(processed: str) -> dict:
            return {"result": processed + "!"}
        
        pipeline = composite_tool(
            step1, step2,
            name="text_pipeline",
            description="Process text through pipeline",
            tags=["composite", "text"]
        )
        
        assert isinstance(pipeline, Tool)
        assert pipeline.name == "text_pipeline"
        assert "composite" in pipeline.metadata.tags
        assert "text" in pipeline.metadata.tags
    
    def test_composite_with_raw_tools(self):
        """Test composite with Tool instances."""
        from src.tools.base_refactored import Tool
        
        class CustomTool(Tool):
            @property
            def metadata(self):
                return ToolMetadata(name="custom", description="Custom tool")
            
            @property
            def parameters(self):
                return []
            
            def _execute_impl(self, **kwargs):
                return {"custom": True}
        
        @tool
        def decorated():
            return {"decorated": True}
        
        # Mix Tool instance and decorated function
        composite = composite_tool(
            CustomTool(),
            decorated,
            name="mixed_composite",
            description="Mixed composite"
        )
        
        assert composite.name == "mixed_composite"
    
    def test_composite_invalid_tool(self):
        """Test composite with invalid tool raises error."""
        def not_a_tool():
            pass
        
        with pytest.raises(ToolError, match="Invalid tool type"):
            composite_tool(
                not_a_tool,
                name="invalid",
                description="Invalid composite"
            )


class TestValidateResult:
    """Test @validate_result decorator."""
    
    def test_validate_raw_result(self):
        """Test validating raw function result."""
        @tool
        @validate_result(lambda x: x > 0, "Result must be positive")
        def calculate(value: int) -> int:
            return value * 2
        
        # Valid result
        result = calculate.tool.execute(value=5)
        assert result.success is True
        assert result.data == 10
        
        # Invalid result
        result = calculate.tool.execute(value=-5)
        assert result.success is False
        assert "must be positive" in result.error
    
    def test_validate_tool_result(self):
        """Test validating ToolResult."""
        @tool
        def process(value: int) -> int:
            return value
        
        @validate_result(lambda x: x != 0, "Result cannot be zero")
        def wrapper(**kwargs):
            return process.tool.execute(**kwargs)
        
        # Valid result
        result = wrapper(value=5)
        assert result.success is True
        
        # Invalid result
        result = wrapper(value=0)
        assert result.success is False
        assert "cannot be zero" in result.error
    
    def test_validate_preserves_tool(self):
        """Test that validate preserves tool attribute."""
        @tool
        @validate_result(lambda x: True)
        def func():
            return "test"
        
        assert hasattr(func, 'tool')
        assert isinstance(func.tool, Tool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])