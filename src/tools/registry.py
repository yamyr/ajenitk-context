"""Tool registry for managing and discovering tools."""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type, Set, Any
import logging

from .base import Tool, AsyncTool, ToolResult, ToolError


logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, Set[str]] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(self, tool: Tool, aliases: Optional[List[str]] = None) -> None:
        """Register a tool instance."""
        if not isinstance(tool, Tool):
            raise ValueError(f"Tool must be an instance of Tool, got {type(tool)}")
        
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        # Register the tool
        self._tools[tool.name] = tool
        
        # Add to category index
        if tool.category not in self._categories:
            self._categories[tool.category] = set()
        self._categories[tool.category].add(tool.name)
        
        # Register aliases
        if aliases:
            for alias in aliases:
                if alias in self._aliases:
                    logger.warning(f"Alias '{alias}' already registered, overwriting")
                self._aliases[alias] = tool.name
        
        logger.info(f"Registered tool: {tool.name} (category: {tool.category})")
    
    def register_class(self, tool_class: Type[Tool], **init_kwargs) -> None:
        """Register a tool class by instantiating it."""
        if not issubclass(tool_class, Tool):
            raise ValueError(f"Tool class must be a subclass of Tool, got {tool_class}")
        
        tool_instance = tool_class(**init_kwargs)
        self.register(tool_instance)
    
    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool."""
        # Resolve alias if needed
        tool_name = self._aliases.get(tool_name, tool_name)
        
        if tool_name not in self._tools:
            return False
        
        tool = self._tools[tool_name]
        
        # Remove from main registry
        del self._tools[tool_name]
        
        # Remove from category index
        if tool.category in self._categories:
            self._categories[tool.category].discard(tool_name)
            if not self._categories[tool.category]:
                del self._categories[tool.category]
        
        # Remove aliases
        aliases_to_remove = [alias for alias, name in self._aliases.items() if name == tool_name]
        for alias in aliases_to_remove:
            del self._aliases[alias]
        
        logger.info(f"Unregistered tool: {tool_name}")
        return True
    
    def get(self, tool_name: str) -> Optional[Tool]:
        """Get a tool by name or alias."""
        # Resolve alias if needed
        tool_name = self._aliases.get(tool_name, tool_name)
        return self._tools.get(tool_name)
    
    def exists(self, tool_name: str) -> bool:
        """Check if a tool exists."""
        tool_name = self._aliases.get(tool_name, tool_name)
        return tool_name in self._tools
    
    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        """List all registered tools, optionally filtered by category."""
        if category:
            tool_names = self._categories.get(category, set())
            return [self._tools[name] for name in tool_names]
        return list(self._tools.values())
    
    def list_categories(self) -> List[str]:
        """List all tool categories."""
        return list(self._categories.keys())
    
    def search(self, query: str, search_in: List[str] = None) -> List[Tool]:
        """Search for tools by name or description."""
        if search_in is None:
            search_in = ["name", "description", "category"]
        
        query_lower = query.lower()
        results = []
        
        for tool in self._tools.values():
            # Search in specified fields
            if "name" in search_in and query_lower in tool.name.lower():
                results.append(tool)
            elif "description" in search_in and query_lower in tool.description.lower():
                results.append(tool)
            elif "category" in search_in and query_lower in tool.category.lower():
                results.append(tool)
        
        return results
    
    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(tool_name)
        if not tool:
            raise ToolError(f"Tool '{tool_name}' not found")
        
        return tool(**kwargs)
    
    def get_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get the schema for a tool."""
        tool = self.get(tool_name)
        if not tool:
            return None
        return tool.get_schema()
    
    def discover_tools(self, package_path: str) -> int:
        """Discover and register tools from a package path."""
        count = 0
        
        try:
            # Import the package
            package = importlib.import_module(package_path)
            
            # Get the package directory
            if hasattr(package, '__path__'):
                # It's a package, scan for modules
                for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                    try:
                        module = importlib.import_module(modname)
                        count += self._register_tools_from_module(module)
                    except Exception as e:
                        logger.error(f"Error importing module {modname}: {e}")
            else:
                # It's a module, scan it directly
                count += self._register_tools_from_module(package)
                
        except Exception as e:
            logger.error(f"Error discovering tools from {package_path}: {e}")
        
        return count
    
    def _register_tools_from_module(self, module) -> int:
        """Register all Tool classes found in a module."""
        count = 0
        
        for name, obj in inspect.getmembers(module):
            # Check if it's a Tool class (but not the base classes)
            if (inspect.isclass(obj) and 
                issubclass(obj, Tool) and 
                obj not in [Tool, AsyncTool] and
                not inspect.isabstract(obj)):
                
                try:
                    # Try to instantiate and register
                    tool_instance = obj()
                    self.register(tool_instance)
                    count += 1
                except Exception as e:
                    logger.error(f"Error registering tool {name}: {e}")
        
        return count
    
    def load_from_directory(self, directory: Path) -> int:
        """Load tools from Python files in a directory."""
        count = 0
        directory = Path(directory)
        
        if not directory.exists() or not directory.is_dir():
            logger.error(f"Directory {directory} does not exist or is not a directory")
            return 0
        
        # Find all Python files
        for py_file in directory.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue
                
            try:
                # Convert file path to module path
                relative_path = py_file.relative_to(directory.parent)
                module_path = str(relative_path.with_suffix("")).replace("/", ".")
                
                # Import and register
                module = importlib.import_module(module_path)
                count += self._register_tools_from_module(module)
                
            except Exception as e:
                logger.error(f"Error loading tools from {py_file}: {e}")
        
        return count
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_tools = len(self._tools)
        tools_by_category = {cat: len(tools) for cat, tools in self._categories.items()}
        
        return {
            "total_tools": total_tools,
            "total_categories": len(self._categories),
            "total_aliases": len(self._aliases),
            "tools_by_category": tools_by_category,
            "async_tools": sum(1 for t in self._tools.values() if isinstance(t, AsyncTool)),
            "safe_tools": sum(1 for t in self._tools.values() if t.is_safe),
            "tools_requiring_confirmation": sum(1 for t in self._tools.values() if t.requires_confirmation)
        }
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._categories.clear()
        self._aliases.clear()
        logger.info("Cleared tool registry")
    
    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if tool exists (supports 'in' operator)."""
        return self.exists(tool_name)
    
    def __getitem__(self, tool_name: str) -> Tool:
        """Get tool by name (supports [] operator)."""
        tool = self.get(tool_name)
        if not tool:
            raise KeyError(f"Tool '{tool_name}' not found")
        return tool


# Global registry instance
tool_registry = ToolRegistry()