"""Refactored tool registry with improved architecture.

This module provides a centralized registry for tool management with
better separation of concerns, caching, and search capabilities.
"""

import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Set, Type, Union, Protocol, Any
from datetime import datetime
import inspect
import importlib
import pkgutil
from pathlib import Path
from threading import RLock
import weakref

from ..exceptions import ToolNotFoundError, ToolError, SecurityError
from ..utils.logging import get_logger
from .base_refactored import Tool, AsyncTool, ToolMetadata, ToolResult

logger = get_logger(__name__)


class ToolFilter(Protocol):
    """Protocol for tool filtering."""
    
    def matches(self, tool: Tool) -> bool:
        """Check if tool matches filter criteria."""
        ...


class CategoryFilter:
    """Filter tools by category."""
    
    def __init__(self, categories: Union[str, List[str]]):
        self.categories = [categories] if isinstance(categories, str) else categories
    
    def matches(self, tool: Tool) -> bool:
        """Check if tool belongs to any of the categories."""
        return tool.metadata.category in self.categories


class TagFilter:
    """Filter tools by tags."""
    
    def __init__(self, tags: Union[str, List[str]], match_all: bool = False):
        self.tags = set([tags] if isinstance(tags, str) else tags)
        self.match_all = match_all
    
    def matches(self, tool: Tool) -> bool:
        """Check if tool has matching tags."""
        tool_tags = set(tool.metadata.tags)
        if self.match_all:
            return self.tags.issubset(tool_tags)
        else:
            return bool(self.tags.intersection(tool_tags))


class SecurityLevel(str, Enum):
    """Security levels for tool execution."""
    UNRESTRICTED = "unrestricted"
    SAFE = "safe"
    SANDBOXED = "sandboxed"
    RESTRICTED = "restricted"


class ToolRegistryIndex:
    """Index for fast tool lookups."""
    
    def __init__(self):
        self._by_category: Dict[str, Set[str]] = defaultdict(set)
        self._by_tag: Dict[str, Set[str]] = defaultdict(set)
        self._by_author: Dict[str, Set[str]] = defaultdict(set)
        self._lock = RLock()
    
    def add(self, tool_name: str, metadata: ToolMetadata) -> None:
        """Add tool to indexes."""
        with self._lock:
            # Index by category
            if metadata.category:
                self._by_category[metadata.category].add(tool_name)
            
            # Index by tags
            for tag in metadata.tags:
                self._by_tag[tag].add(tool_name)
            
            # Index by author
            if metadata.author:
                self._by_author[metadata.author].add(tool_name)
    
    def remove(self, tool_name: str, metadata: ToolMetadata) -> None:
        """Remove tool from indexes."""
        with self._lock:
            # Remove from category index
            if metadata.category:
                self._by_category[metadata.category].discard(tool_name)
            
            # Remove from tag index
            for tag in metadata.tags:
                self._by_tag[tag].discard(tool_name)
            
            # Remove from author index
            if metadata.author:
                self._by_author[metadata.author].discard(tool_name)
    
    def find_by_category(self, category: str) -> Set[str]:
        """Find tools by category."""
        with self._lock:
            return self._by_category.get(category, set()).copy()
    
    def find_by_tag(self, tag: str) -> Set[str]:
        """Find tools by tag."""
        with self._lock:
            return self._by_tag.get(tag, set()).copy()
    
    def find_by_author(self, author: str) -> Set[str]:
        """Find tools by author."""
        with self._lock:
            return self._by_author.get(author, set()).copy()


class ToolRegistry:
    """Centralized registry for tool management with improved features."""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.SAFE):
        """Initialize registry.
        
        Args:
            security_level: Default security level for tool execution
        """
        self._tools: Dict[str, Tool] = {}
        self._aliases: Dict[str, str] = {}
        self._index = ToolRegistryIndex()
        self._security_level = security_level
        self._lock = RLock()
        self._weak_refs: Dict[str, weakref.ref] = {}
        self._execution_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
    
    @property
    def security_level(self) -> SecurityLevel:
        """Get current security level."""
        return self._security_level
    
    def set_security_level(self, level: SecurityLevel) -> None:
        """Set security level for tool execution."""
        logger.info(f"Setting security level to: {level}")
        self._security_level = level
    
    def register(self, 
                tool: Union[Tool, Type[Tool]], 
                aliases: Optional[List[str]] = None,
                replace: bool = False) -> None:
        """Register a tool with the registry.
        
        Args:
            tool: Tool instance or class
            aliases: Optional list of aliases
            replace: Whether to replace existing tool
            
        Raises:
            ToolError: If registration fails
        """
        # Handle tool class
        if inspect.isclass(tool):
            try:
                tool = tool()
            except Exception as e:
                raise ToolError(f"Failed to instantiate tool class: {str(e)}")
        
        if not isinstance(tool, Tool):
            raise ToolError(f"Invalid tool type: {type(tool)}")
        
        tool_name = tool.name
        
        with self._lock:
            # Check if tool already exists
            if tool_name in self._tools and not replace:
                raise ToolError(f"Tool '{tool_name}' already registered")
            
            # Unregister old tool if replacing
            if tool_name in self._tools:
                self.unregister(tool_name)
            
            # Register tool
            self._tools[tool_name] = tool
            self._weak_refs[tool_name] = weakref.ref(tool)
            
            # Add to index
            self._index.add(tool_name, tool.metadata)
            
            # Register aliases
            if aliases:
                for alias in aliases:
                    if alias in self._aliases and not replace:
                        raise ToolError(f"Alias '{alias}' already in use")
                    self._aliases[alias] = tool_name
            
            logger.info(f"Registered tool: {tool_name}")
    
    def unregister(self, name: str) -> None:
        """Unregister a tool.
        
        Args:
            name: Tool name or alias
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        with self._lock:
            # Resolve alias
            tool_name = self._aliases.get(name, name)
            
            if tool_name not in self._tools:
                raise ToolNotFoundError(tool_name)
            
            # Get tool for metadata
            tool = self._tools[tool_name]
            
            # Remove from index
            self._index.remove(tool_name, tool.metadata)
            
            # Remove tool
            del self._tools[tool_name]
            del self._weak_refs[tool_name]
            
            # Remove aliases
            aliases_to_remove = [
                alias for alias, target in self._aliases.items()
                if target == tool_name
            ]
            for alias in aliases_to_remove:
                del self._aliases[alias]
            
            # Remove stats
            if tool_name in self._execution_stats:
                del self._execution_stats[tool_name]
            
            logger.info(f"Unregistered tool: {tool_name}")
    
    def get(self, name: str) -> Tool:
        """Get a tool by name or alias.
        
        Args:
            name: Tool name or alias
            
        Returns:
            Tool instance
            
        Raises:
            ToolNotFoundError: If tool not found
        """
        with self._lock:
            # Resolve alias
            tool_name = self._aliases.get(name, name)
            
            if tool_name not in self._tools:
                raise ToolNotFoundError(name)
            
            return self._tools[tool_name]
    
    def exists(self, name: str) -> bool:
        """Check if a tool exists.
        
        Args:
            name: Tool name or alias
            
        Returns:
            True if tool exists
        """
        with self._lock:
            tool_name = self._aliases.get(name, name)
            return tool_name in self._tools
    
    def list_tools(self, 
                  filter_func: Optional[ToolFilter] = None,
                  include_deprecated: bool = False) -> List[Tool]:
        """List all registered tools with optional filtering.
        
        Args:
            filter_func: Optional filter function
            include_deprecated: Whether to include deprecated tools
            
        Returns:
            List of tools
        """
        with self._lock:
            tools = list(self._tools.values())
        
        # Filter deprecated
        if not include_deprecated:
            tools = [t for t in tools if not t.metadata.deprecated]
        
        # Apply custom filter
        if filter_func:
            tools = [t for t in tools if filter_func.matches(t)]
        
        return tools
    
    def search(self, 
              query: str,
              search_fields: Optional[List[str]] = None) -> List[Tool]:
        """Search for tools by query string.
        
        Args:
            query: Search query
            search_fields: Fields to search in (name, description, tags)
            
        Returns:
            List of matching tools
        """
        if search_fields is None:
            search_fields = ['name', 'description', 'tags']
        
        query_lower = query.lower()
        results = []
        
        with self._lock:
            for tool in self._tools.values():
                # Search in name
                if 'name' in search_fields and query_lower in tool.name.lower():
                    results.append(tool)
                    continue
                
                # Search in description
                if 'description' in search_fields and query_lower in tool.description.lower():
                    results.append(tool)
                    continue
                
                # Search in tags
                if 'tags' in search_fields:
                    if any(query_lower in tag.lower() for tag in tool.metadata.tags):
                        results.append(tool)
        
        return results
    
    def get_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of tools in the category
        """
        tool_names = self._index.find_by_category(category)
        return [self.get(name) for name in tool_names if self.exists(name)]
    
    def get_by_tag(self, tag: str) -> List[Tool]:
        """Get all tools with a specific tag.
        
        Args:
            tag: Tag name
            
        Returns:
            List of tools with the tag
        """
        tool_names = self._index.find_by_tag(tag)
        return [self.get(name) for name in tool_names if self.exists(name)]
    
    def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name with security checks.
        
        Args:
            name: Tool name or alias
            **kwargs: Tool parameters
            
        Returns:
            ToolResult instance
            
        Raises:
            ToolNotFoundError: If tool not found
            SecurityError: If execution blocked by security policy
        """
        tool = self.get(name)
        
        # Security check
        if not self._check_security(tool):
            raise SecurityError(
                message=f"Tool '{name}' execution blocked by security policy",
                security_level=self._security_level.value,
                attempted_action=f"execute tool '{name}'"
            )
        
        # Update stats
        start_time = datetime.utcnow()
        
        try:
            result = tool.execute(**kwargs)
            
            # Update execution stats
            self._update_stats(tool.name, success=True, 
                             execution_time=result.execution_time)
            
            return result
            
        except Exception as e:
            # Update failure stats
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_stats(tool.name, success=False, 
                             execution_time=execution_time)
            raise
    
    async def execute_async(self, name: str, **kwargs) -> ToolResult:
        """Execute an async tool by name.
        
        Args:
            name: Tool name or alias
            **kwargs: Tool parameters
            
        Returns:
            ToolResult instance
        """
        tool = self.get(name)
        
        if not isinstance(tool, AsyncTool):
            # Fall back to sync execution in thread pool
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.execute, name, **kwargs)
        
        # Security check
        if not self._check_security(tool):
            raise SecurityError(
                message=f"Tool '{name}' execution blocked by security policy",
                security_level=self._security_level.value,
                attempted_action=f"execute async tool '{name}'"
            )
        
        return await tool.execute_async(**kwargs)
    
    def _check_security(self, tool: Tool) -> bool:
        """Check if tool execution is allowed under current security level.
        
        Args:
            tool: Tool to check
            
        Returns:
            True if execution is allowed
        """
        # Define restricted tools/tags per security level
        if self._security_level == SecurityLevel.UNRESTRICTED:
            return True
        
        restricted_tags = {
            SecurityLevel.SAFE: {'system', 'network', 'dangerous'},
            SecurityLevel.SANDBOXED: {'system', 'network', 'file_write', 'dangerous'},
            SecurityLevel.RESTRICTED: {'system', 'network', 'file_write', 'file_read', 'dangerous'}
        }
        
        tool_tags = set(tool.metadata.tags)
        restricted = restricted_tags.get(self._security_level, set())
        
        return not bool(tool_tags.intersection(restricted))
    
    def _update_stats(self, tool_name: str, success: bool, 
                     execution_time: float) -> None:
        """Update execution statistics for a tool."""
        with self._lock:
            stats = self._execution_stats[tool_name]
            
            # Initialize if needed
            if not stats:
                stats.update({
                    'total_executions': 0,
                    'successful_executions': 0,
                    'failed_executions': 0,
                    'total_execution_time': 0.0,
                    'min_execution_time': float('inf'),
                    'max_execution_time': 0.0
                })
            
            # Update counts
            stats['total_executions'] += 1
            if success:
                stats['successful_executions'] += 1
            else:
                stats['failed_executions'] += 1
            
            # Update times
            stats['total_execution_time'] += execution_time
            stats['min_execution_time'] = min(stats['min_execution_time'], execution_time)
            stats['max_execution_time'] = max(stats['max_execution_time'], execution_time)
    
    def get_statistics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics.
        
        Args:
            name: Tool name for specific stats, or None for all
            
        Returns:
            Statistics dictionary
        """
        with self._lock:
            if name:
                tool_name = self._aliases.get(name, name)
                return self._execution_stats.get(tool_name, {}).copy()
            else:
                return dict(self._execution_stats)
    
    def discover_tools(self, 
                      package_name: str,
                      recursive: bool = True) -> int:
        """Discover and register tools from a package.
        
        Args:
            package_name: Package to scan for tools
            recursive: Whether to scan subpackages
            
        Returns:
            Number of tools discovered
        """
        count = 0
        
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            logger.error(f"Failed to import package {package_name}: {e}")
            return 0
        
        # Get package path
        if hasattr(package, '__path__'):
            package_path = package.__path__
        else:
            # Single module
            return self._discover_in_module(package)
        
        # Scan package
        for importer, modname, ispkg in pkgutil.walk_packages(
            package_path, 
            prefix=package_name + ".",
            onerror=lambda x: logger.error(f"Error scanning package: {x}")
        ):
            if not recursive and ispkg:
                continue
                
            try:
                module = importlib.import_module(modname)
                count += self._discover_in_module(module)
            except Exception as e:
                logger.error(f"Error importing {modname}: {e}")
        
        logger.info(f"Discovered {count} tools in {package_name}")
        return count
    
    def _discover_in_module(self, module) -> int:
        """Discover tools in a module."""
        count = 0
        
        for name, obj in inspect.getmembers(module):
            # Check if it's a Tool subclass (but not Tool itself)
            if (inspect.isclass(obj) and 
                issubclass(obj, Tool) and 
                obj is not Tool and
                obj is not AsyncTool):
                
                try:
                    self.register(obj)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to register {name}: {e}")
        
        return count