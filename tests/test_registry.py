"""Tests for refactored tool registry."""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.tools.registry_refactored import (
    ToolRegistry, ToolRegistryIndex, CategoryFilter, TagFilter,
    SecurityLevel
)
from src.tools.base_refactored import Tool, AsyncTool, ToolMetadata, ToolParameter, ToolParameterType
from src.exceptions import ToolNotFoundError, ToolError, SecurityError


class MockTool(Tool):
    """Mock tool for testing."""
    
    def __init__(self, name: str, category: str = None, tags: list = None):
        self._name = name
        self._category = category
        self._tags = tags or []
        super().__init__()
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self._name,
            description=f"Mock tool {self._name}",
            category=self._category,
            tags=self._tags
        )
    
    @property
    def parameters(self) -> list:
        return []
    
    def _execute_impl(self, **kwargs):
        return {"tool": self._name, "params": kwargs}


class MockAsyncTool(AsyncTool):
    """Mock async tool for testing."""
    
    def __init__(self, name: str):
        self._name = name
        super().__init__()
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self._name,
            description=f"Mock async tool {self._name}"
        )
    
    @property
    def parameters(self) -> list:
        return []
    
    async def _execute_impl_async(self, **kwargs):
        await asyncio.sleep(0.01)
        return {"async_tool": self._name, "params": kwargs}


class TestToolRegistryIndex:
    """Test ToolRegistryIndex class."""
    
    def test_add_to_index(self):
        """Test adding tools to index."""
        index = ToolRegistryIndex()
        metadata = ToolMetadata(
            name="test_tool",
            description="Test",
            category="utilities",
            tags=["test", "mock"],
            author="Test Author"
        )
        
        index.add("test_tool", metadata)
        
        assert "test_tool" in index.find_by_category("utilities")
        assert "test_tool" in index.find_by_tag("test")
        assert "test_tool" in index.find_by_tag("mock")
        assert "test_tool" in index.find_by_author("Test Author")
    
    def test_remove_from_index(self):
        """Test removing tools from index."""
        index = ToolRegistryIndex()
        metadata = ToolMetadata(
            name="test_tool",
            description="Test",
            category="utilities",
            tags=["test"]
        )
        
        index.add("test_tool", metadata)
        index.remove("test_tool", metadata)
        
        assert "test_tool" not in index.find_by_category("utilities")
        assert "test_tool" not in index.find_by_tag("test")
    
    def test_find_nonexistent(self):
        """Test finding in empty categories."""
        index = ToolRegistryIndex()
        
        assert index.find_by_category("nonexistent") == set()
        assert index.find_by_tag("nonexistent") == set()
        assert index.find_by_author("nonexistent") == set()


class TestFilters:
    """Test filter classes."""
    
    def test_category_filter(self):
        """Test CategoryFilter."""
        filter_single = CategoryFilter("utilities")
        filter_multi = CategoryFilter(["utilities", "network"])
        
        tool1 = MockTool("tool1", category="utilities")
        tool2 = MockTool("tool2", category="network")
        tool3 = MockTool("tool3", category="other")
        
        assert filter_single.matches(tool1) is True
        assert filter_single.matches(tool2) is False
        assert filter_single.matches(tool3) is False
        
        assert filter_multi.matches(tool1) is True
        assert filter_multi.matches(tool2) is True
        assert filter_multi.matches(tool3) is False
    
    def test_tag_filter(self):
        """Test TagFilter."""
        filter_any = TagFilter(["test", "mock"])
        filter_all = TagFilter(["test", "mock"], match_all=True)
        
        tool1 = MockTool("tool1", tags=["test", "mock"])
        tool2 = MockTool("tool2", tags=["test"])
        tool3 = MockTool("tool3", tags=["other"])
        
        # Match any tag
        assert filter_any.matches(tool1) is True
        assert filter_any.matches(tool2) is True
        assert filter_any.matches(tool3) is False
        
        # Match all tags
        assert filter_all.matches(tool1) is True
        assert filter_all.matches(tool2) is False
        assert filter_all.matches(tool3) is False


class TestToolRegistry:
    """Test ToolRegistry class."""
    
    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        
        registry.register(tool)
        
        assert registry.exists("test_tool")
        assert registry.get("test_tool") == tool
    
    def test_register_tool_class(self):
        """Test registering a tool class."""
        registry = ToolRegistry()
        
        class TestToolClass(MockTool):
            def __init__(self):
                super().__init__("class_tool")
        
        registry.register(TestToolClass)
        
        assert registry.exists("class_tool")
        assert isinstance(registry.get("class_tool"), TestToolClass)
    
    def test_register_with_aliases(self):
        """Test registering with aliases."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        
        registry.register(tool, aliases=["alias1", "alias2"])
        
        assert registry.get("alias1") == tool
        assert registry.get("alias2") == tool
        assert registry.get("test_tool") == tool
    
    def test_register_duplicate_error(self):
        """Test that duplicate registration raises error."""
        registry = ToolRegistry()
        tool1 = MockTool("test_tool")
        tool2 = MockTool("test_tool")
        
        registry.register(tool1)
        
        with pytest.raises(ToolError, match="already registered"):
            registry.register(tool2)
    
    def test_register_replace(self):
        """Test replacing an existing tool."""
        registry = ToolRegistry()
        tool1 = MockTool("test_tool", tags=["old"])
        tool2 = MockTool("test_tool", tags=["new"])
        
        registry.register(tool1)
        registry.register(tool2, replace=True)
        
        registered_tool = registry.get("test_tool")
        assert "new" in registered_tool.metadata.tags
        assert "old" not in registered_tool.metadata.tags
    
    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        
        registry.register(tool, aliases=["alias1"])
        registry.unregister("test_tool")
        
        assert not registry.exists("test_tool")
        assert not registry.exists("alias1")
    
    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent tool raises error."""
        registry = ToolRegistry()
        
        with pytest.raises(ToolNotFoundError):
            registry.unregister("nonexistent")
    
    def test_get_nonexistent(self):
        """Test getting nonexistent tool raises error."""
        registry = ToolRegistry()
        
        with pytest.raises(ToolNotFoundError):
            registry.get("nonexistent")
    
    def test_list_tools(self):
        """Test listing tools."""
        registry = ToolRegistry()
        tool1 = MockTool("tool1", category="cat1")
        tool2 = MockTool("tool2", category="cat2")
        
        registry.register(tool1)
        registry.register(tool2)
        
        tools = registry.list_tools()
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools
    
    def test_list_tools_with_filter(self):
        """Test listing tools with filter."""
        registry = ToolRegistry()
        tool1 = MockTool("tool1", category="utilities")
        tool2 = MockTool("tool2", category="network")
        
        registry.register(tool1)
        registry.register(tool2)
        
        filter_func = CategoryFilter("utilities")
        tools = registry.list_tools(filter_func=filter_func)
        
        assert len(tools) == 1
        assert tool1 in tools
        assert tool2 not in tools
    
    def test_list_tools_exclude_deprecated(self):
        """Test excluding deprecated tools."""
        registry = ToolRegistry()
        
        # Create deprecated tool
        class DeprecatedTool(MockTool):
            @property
            def metadata(self):
                meta = super().metadata
                meta.deprecated = True
                return meta
        
        tool1 = MockTool("tool1")
        tool2 = DeprecatedTool("tool2")
        
        registry.register(tool1)
        registry.register(tool2)
        
        # Default excludes deprecated
        tools = registry.list_tools()
        assert len(tools) == 1
        assert tool1 in tools
        
        # Include deprecated
        tools = registry.list_tools(include_deprecated=True)
        assert len(tools) == 2
    
    def test_search_tools(self):
        """Test searching tools."""
        registry = ToolRegistry()
        tool1 = MockTool("calculator", tags=["math", "utility"])
        tool2 = MockTool("string_processor", tags=["text", "utility"])
        
        registry.register(tool1)
        registry.register(tool2)
        
        # Search by name
        results = registry.search("calc")
        assert len(results) == 1
        assert tool1 in results
        
        # Search by tag
        results = registry.search("utility")
        assert len(results) == 2
        
        # Search by description
        results = registry.search("mock tool")
        assert len(results) == 2
    
    def test_get_by_category(self):
        """Test getting tools by category."""
        registry = ToolRegistry()
        tool1 = MockTool("tool1", category="utilities")
        tool2 = MockTool("tool2", category="utilities")
        tool3 = MockTool("tool3", category="network")
        
        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)
        
        utils = registry.get_by_category("utilities")
        assert len(utils) == 2
        assert tool1 in utils
        assert tool2 in utils
        assert tool3 not in utils
    
    def test_get_by_tag(self):
        """Test getting tools by tag."""
        registry = ToolRegistry()
        tool1 = MockTool("tool1", tags=["test", "mock"])
        tool2 = MockTool("tool2", tags=["test"])
        tool3 = MockTool("tool3", tags=["other"])
        
        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)
        
        test_tools = registry.get_by_tag("test")
        assert len(test_tools) == 2
        assert tool1 in test_tools
        assert tool2 in test_tools
        assert tool3 not in test_tools
    
    def test_execute_tool(self):
        """Test executing a tool through registry."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        
        result = registry.execute("test_tool", param1="value1")
        
        assert result.success is True
        assert result.data == {"tool": "test_tool", "params": {"param1": "value1"}}
    
    @pytest.mark.asyncio
    async def test_execute_async_tool(self):
        """Test executing async tool."""
        registry = ToolRegistry()
        tool = MockAsyncTool("async_tool")
        registry.register(tool)
        
        result = await registry.execute_async("async_tool", param1="value1")
        
        assert result.success is True
        assert result.data == {"async_tool": "async_tool", "params": {"param1": "value1"}}
    
    def test_security_levels(self):
        """Test security level enforcement."""
        registry = ToolRegistry(security_level=SecurityLevel.SAFE)
        
        # Create tool with dangerous tag
        dangerous_tool = MockTool("dangerous", tags=["dangerous"])
        safe_tool = MockTool("safe", tags=["utility"])
        
        registry.register(dangerous_tool)
        registry.register(safe_tool)
        
        # Safe tool should execute
        result = registry.execute("safe")
        assert result.success is True
        
        # Dangerous tool should be blocked
        with pytest.raises(SecurityError):
            registry.execute("dangerous")
        
        # Change security level
        registry.set_security_level(SecurityLevel.UNRESTRICTED)
        result = registry.execute("dangerous")
        assert result.success is True
    
    def test_execution_statistics(self):
        """Test tracking execution statistics."""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        
        # Initial stats should be empty
        stats = registry.get_statistics("test_tool")
        assert stats == {}
        
        # Execute tool
        registry.execute("test_tool")
        
        # Check stats
        stats = registry.get_statistics("test_tool")
        assert stats["total_executions"] == 1
        assert stats["successful_executions"] == 1
        assert stats["failed_executions"] == 0
        assert stats["total_execution_time"] > 0
        
        # Test failed execution
        class FailingTool(MockTool):
            def _execute_impl(self, **kwargs):
                raise Exception("Test failure")
        
        failing = FailingTool("failing")
        registry.register(failing)
        
        try:
            registry.execute("failing")
        except:
            pass
        
        stats = registry.get_statistics("failing")
        assert stats["failed_executions"] == 1
    
    def test_discover_tools(self):
        """Test tool discovery."""
        registry = ToolRegistry()
        
        # Mock a module with tools
        mock_module = Mock()
        mock_module.__name__ = "test_module"
        
        # Add tool classes to module
        setattr(mock_module, "Tool1", type("Tool1", (MockTool,), {
            "__init__": lambda self: MockTool.__init__(self, "discovered1")
        }))
        setattr(mock_module, "Tool2", type("Tool2", (MockTool,), {
            "__init__": lambda self: MockTool.__init__(self, "discovered2")
        }))
        setattr(mock_module, "NotATool", str)  # Should be ignored
        
        with patch("importlib.import_module", return_value=mock_module):
            count = registry._discover_in_module(mock_module)
        
        assert count == 2
        assert registry.exists("discovered1")
        assert registry.exists("discovered2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])