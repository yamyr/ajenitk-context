"""Tests for the tool system."""

import pytest
from pathlib import Path
import tempfile
import json

from src.tools import (
    Tool, ToolResult, ToolParameter, ToolParameterType, ToolError,
    tool_registry, tool, async_tool,
    ToolValidator, SecurityLevel,
    ToolDocumentationGenerator
)
from src.tools.builtin import ReadFileTool, WriteFileTool, ListDirectoryTool


class TestToolBase:
    """Test base tool functionality."""
    
    def test_tool_creation(self):
        """Test creating a basic tool."""
        class SimpleTestTool(Tool):
            @property
            def name(self) -> str:
                return "test_tool"
            
            @property
            def description(self) -> str:
                return "A test tool"
            
            def parameters(self):
                return [
                    ToolParameter(
                        name="input",
                        type=ToolParameterType.STRING,
                        description="Test input",
                        required=True
                    )
                ]
            
            def execute(self, input: str) -> ToolResult:
                return ToolResult(
                    success=True,
                    data={"output": f"Processed: {input}"}
                )
        
        tool = SimpleTestTool()
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.category == "general"
        assert tool.is_safe == True
        
        # Test execution
        result = tool(input="test")
        assert result.success == True
        assert result.data["output"] == "Processed: test"
    
    def test_parameter_validation(self):
        """Test parameter validation."""
        class ValidatedTool(Tool):
            @property
            def name(self) -> str:
                return "validated_tool"
            
            @property
            def description(self) -> str:
                return "Tool with validation"
            
            def parameters(self):
                return [
                    ToolParameter(
                        name="required_param",
                        type=ToolParameterType.STRING,
                        description="Required parameter",
                        required=True
                    ),
                    ToolParameter(
                        name="optional_param",
                        type=ToolParameterType.INTEGER,
                        description="Optional parameter",
                        required=False,
                        default=42
                    )
                ]
            
            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True, data=kwargs)
        
        tool = ValidatedTool()
        
        # Test missing required parameter
        with pytest.raises(ToolError) as exc_info:
            tool()
        assert "Required parameter 'required_param' not provided" in str(exc_info.value)
        
        # Test unknown parameter
        with pytest.raises(ToolError) as exc_info:
            tool(required_param="test", unknown="value")
        assert "Unknown parameters: unknown" in str(exc_info.value)
        
        # Test valid execution
        result = tool(required_param="test")
        assert result.success == True
        assert result.data["required_param"] == "test"
        assert result.data["optional_param"] == 42


class TestToolDecorators:
    """Test tool decorators."""
    
    def test_tool_decorator(self):
        """Test @tool decorator."""
        @tool(
            name="decorated_tool",
            description="A decorated tool",
            category="test",
            version="2.0.0",
            register=False
        )
        def my_tool(text: str, count: int = 1) -> dict:
            """Process text multiple times."""
            return {"result": text * count}
        
        # Check tool properties
        tool_instance = my_tool.tool
        assert tool_instance.name == "decorated_tool"
        assert tool_instance.description == "A decorated tool"
        assert tool_instance.category == "test"
        assert tool_instance.version == "2.0.0"
        
        # Check parameters were extracted
        params = tool_instance.parameters()
        assert len(params) == 2
        assert params[0].name == "text"
        assert params[0].type == ToolParameterType.STRING
        assert params[0].required == True
        assert params[1].name == "count"
        assert params[1].type == ToolParameterType.INTEGER
        assert params[1].required == False
        assert params[1].default == 1
        
        # Test execution
        result = tool_instance(text="hello", count=3)
        assert result.success == True
        assert result.data["result"] == "hellohellohello"
    
    @pytest.mark.asyncio
    async def test_async_tool_decorator(self):
        """Test @async_tool decorator."""
        @async_tool(
            name="async_decorated",
            description="An async tool",
            register=False
        )
        async def async_operation(delay: float = 0.1) -> str:
            """Simulate async operation."""
            import asyncio
            await asyncio.sleep(delay)
            return f"Completed after {delay}s"
        
        tool_instance = async_operation.tool
        assert tool_instance.name == "async_decorated"
        
        # Test async execution
        result = await tool_instance.execute(delay=0.01)
        assert result.success == True
        assert "Completed after 0.01s" in result.data


class TestToolRegistry:
    """Test tool registry functionality."""
    
    def test_register_and_get(self):
        """Test registering and retrieving tools."""
        registry = tool_registry
        
        # Create a test tool
        @tool(name="registry_test", register=False)
        def test_tool() -> str:
            return "test"
        
        # Register tool
        registry.register(test_tool.tool)
        
        # Get tool
        retrieved = registry.get("registry_test")
        assert retrieved is not None
        assert retrieved.name == "registry_test"
        
        # Check existence
        assert registry.exists("registry_test")
        assert "registry_test" in registry
        
        # Clean up
        registry.unregister("registry_test")
    
    def test_aliases(self):
        """Test tool aliases."""
        registry = tool_registry
        
        @tool(name="aliased_tool", register=False)
        def test_tool() -> str:
            return "test"
        
        # Register with aliases
        registry.register(test_tool.tool, aliases=["alias1", "alias2"])
        
        # Get by aliases
        assert registry.get("alias1") == test_tool.tool
        assert registry.get("alias2") == test_tool.tool
        assert registry.get("aliased_tool") == test_tool.tool
        
        # Clean up
        registry.unregister("aliased_tool")
    
    def test_search(self):
        """Test searching tools."""
        registry = tool_registry
        
        @tool(
            name="searchable_tool",
            description="Tool for testing search functionality",
            category="search_test",
            register=False
        )
        def test_tool() -> str:
            return "test"
        
        registry.register(test_tool.tool)
        
        # Search by name
        results = registry.search("searchable")
        assert len(results) >= 1
        assert any(t.name == "searchable_tool" for t in results)
        
        # Search by description
        results = registry.search("testing search")
        assert len(results) >= 1
        
        # Search by category
        results = registry.search("search_test")
        assert len(results) >= 1
        
        # Clean up
        registry.unregister("searchable_tool")


class TestBuiltinTools:
    """Test built-in file system tools."""
    
    def test_read_file_tool(self):
        """Test ReadFileTool."""
        tool = ReadFileTool()
        
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            # Test reading
            result = tool(path=temp_path)
            assert result.success == True
            assert result.data == "Test content"
            
            # Test non-existent file
            result = tool(path="/nonexistent/file.txt")
            assert result.success == False
            assert "does not exist" in result.error
        finally:
            Path(temp_path).unlink()
    
    def test_write_file_tool(self):
        """Test WriteFileTool."""
        tool = WriteFileTool()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"
            
            # Test writing
            result = tool(
                path=str(file_path),
                content="Hello, World!",
                overwrite=True
            )
            assert result.success == True
            assert file_path.read_text() == "Hello, World!"
            
            # Test overwrite protection
            result = tool(
                path=str(file_path),
                content="New content",
                overwrite=False
            )
            assert result.success == False
            assert "already exists" in result.error
    
    def test_list_directory_tool(self):
        """Test ListDirectoryTool."""
        tool = ListDirectoryTool()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            Path(temp_dir, "file1.txt").write_text("content1")
            Path(temp_dir, "file2.py").write_text("content2")
            Path(temp_dir, "subdir").mkdir()
            Path(temp_dir, "subdir", "file3.txt").write_text("content3")
            
            # Test listing
            result = tool(path=temp_dir)
            assert result.success == True
            assert len(result.data) == 3
            
            # Test recursive listing
            result = tool(path=temp_dir, recursive=True)
            assert result.success == True
            assert len(result.data) == 4
            
            # Test pattern filtering
            result = tool(path=temp_dir, pattern="*.txt")
            assert result.success == True
            assert len(result.data) == 1
            assert result.data[0]["name"] == "file1.txt"


class TestToolValidation:
    """Test tool validation and security."""
    
    def test_security_validation(self):
        """Test security validation."""
        validator = ToolValidator(SecurityLevel.SAFE)
        
        @tool(name="safe_tool", register=False)
        def safe_operation(text: str) -> str:
            return text.upper()
        
        # Validate safe tool
        results = validator.validate_tool(safe_operation.tool)
        assert results["valid"] == True
        assert len(results["errors"]) == 0
    
    def test_parameter_validation(self):
        """Test parameter validation."""
        validator = ToolValidator()
        
        class BadParamTool(Tool):
            @property
            def name(self) -> str:
                return "bad_param_tool"
            
            @property
            def description(self) -> str:
                return "Tool with bad parameters"
            
            def parameters(self):
                return [
                    ToolParameter(
                        name="123invalid",  # Invalid name
                        type=ToolParameterType.STRING,
                        description="Bad parameter",
                        required=True
                    ),
                    ToolParameter(
                        name="duplicate",
                        type=ToolParameterType.STRING,
                        description="",  # Missing description
                        required=True
                    ),
                    ToolParameter(
                        name="duplicate",  # Duplicate name
                        type=ToolParameterType.STRING,
                        description="Duplicate",
                        required=True
                    )
                ]
            
            def execute(self, **kwargs) -> ToolResult:
                return ToolResult(success=True)
        
        tool = BadParamTool()
        results = validator.validate_tool(tool)
        assert results["valid"] == False
        assert any("Invalid parameter name" in e for e in results["errors"])
        assert any("Duplicate parameter name" in e for e in results["errors"])
        assert any("meaningful description" in w for w in results["warnings"])


class TestToolDocumentation:
    """Test tool documentation generation."""
    
    def test_markdown_generation(self):
        """Test generating Markdown documentation."""
        @tool(name="doc_test_tool", description="Tool for documentation testing", register=False)
        def test_tool(param1: str, param2: int = 10) -> dict:
            """A test tool for documentation."""
            return {"result": f"{param1}:{param2}"}
        
        doc_gen = ToolDocumentationGenerator()
        markdown = doc_gen.generate_markdown([test_tool.tool], include_toc=False)
        
        assert "doc_test_tool" in markdown
        assert "Tool for documentation testing" in markdown
        assert "param1" in markdown
        assert "param2" in markdown
        assert "Default" in markdown
        assert "10" in markdown
    
    def test_json_schema_generation(self):
        """Test generating JSON schema."""
        @tool(name="schema_test", register=False)
        def test_tool() -> str:
            return "test"
        
        doc_gen = ToolDocumentationGenerator()
        schema = doc_gen.generate_json_schema([test_tool.tool])
        
        assert "schema" in schema
        assert "tools" in schema
        assert len(schema["tools"]) == 1
        assert schema["tools"][0]["name"] == "schema_test"
    
    def test_openapi_generation(self):
        """Test generating OpenAPI spec."""
        @tool(name="api_test", register=False)
        def test_tool(query: str) -> dict:
            return {"result": query}
        
        doc_gen = ToolDocumentationGenerator()
        spec = doc_gen.generate_openapi_spec([test_tool.tool])
        
        assert spec["openapi"] == "3.0.0"
        assert "/tools/general/api_test" in spec["paths"]
        assert "post" in spec["paths"]["/tools/general/api_test"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])