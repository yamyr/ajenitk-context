"""Dynamic tool loading and discovery mechanisms."""

import os
import sys
import yaml
import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
import logging

from .base import Tool
from .registry import tool_registry


logger = logging.getLogger(__name__)


class ToolLoader:
    """Handles dynamic loading of tools from various sources."""
    
    def __init__(self, registry: Optional['ToolRegistry'] = None):
        self.registry = registry or tool_registry
        self.loaded_modules: Dict[str, Any] = {}
    
    def load_from_module(self, module_path: str) -> int:
        """Load tools from a Python module path.
        
        Args:
            module_path: Dotted module path (e.g., 'mypackage.tools')
        
        Returns:
            Number of tools loaded
        """
        return self.registry.discover_tools(module_path)
    
    def load_from_file(self, file_path: Path) -> int:
        """Load tools from a Python file.
        
        Args:
            file_path: Path to Python file containing tool definitions
        
        Returns:
            Number of tools loaded
        """
        file_path = Path(file_path).resolve()
        
        if not file_path.exists():
            raise FileNotFoundError(f"Tool file not found: {file_path}")
        
        if not file_path.suffix == '.py':
            raise ValueError(f"Tool file must be a Python file: {file_path}")
        
        # Create module name from file
        module_name = f"ajentik_tools_{file_path.stem}"
        
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Store reference
        self.loaded_modules[str(file_path)] = module
        
        # Register tools from module
        return self.registry._register_tools_from_module(module)
    
    def load_from_directory(self, directory: Path, recursive: bool = True) -> int:
        """Load all tools from a directory.
        
        Args:
            directory: Directory containing tool files
            recursive: Whether to search subdirectories
        
        Returns:
            Total number of tools loaded
        """
        directory = Path(directory).resolve()
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        count = 0
        pattern = "**/*.py" if recursive else "*.py"
        
        for py_file in directory.glob(pattern):
            # Skip __pycache__ and hidden files
            if '__pycache__' in str(py_file) or py_file.name.startswith('.'):
                continue
            
            # Skip __init__.py files
            if py_file.name == '__init__.py':
                continue
            
            try:
                loaded = self.load_from_file(py_file)
                count += loaded
                logger.info(f"Loaded {loaded} tools from {py_file}")
            except Exception as e:
                logger.error(f"Error loading tools from {py_file}: {e}")
        
        return count
    
    def load_from_config(self, config_path: Path) -> int:
        """Load tools from a configuration file.
        
        The config file can be YAML or JSON and should have the structure:
        {
            "tools": [
                {
                    "type": "module",
                    "path": "mypackage.tools"
                },
                {
                    "type": "file",
                    "path": "/path/to/tool.py"
                },
                {
                    "type": "directory",
                    "path": "/path/to/tools/",
                    "recursive": true
                }
            ]
        }
        
        Args:
            config_path: Path to configuration file
        
        Returns:
            Total number of tools loaded
        """
        config_path = Path(config_path).resolve()
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        # Load config
        with open(config_path, 'r') as f:
            if config_path.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            elif config_path.suffix == '.json':
                config = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_path.suffix}")
        
        count = 0
        tools_config = config.get('tools', [])
        
        for tool_spec in tools_config:
            tool_type = tool_spec.get('type')
            tool_path = tool_spec.get('path')
            
            if not tool_type or not tool_path:
                logger.warning(f"Invalid tool specification: {tool_spec}")
                continue
            
            try:
                if tool_type == 'module':
                    loaded = self.load_from_module(tool_path)
                elif tool_type == 'file':
                    loaded = self.load_from_file(Path(tool_path))
                elif tool_type == 'directory':
                    recursive = tool_spec.get('recursive', True)
                    loaded = self.load_from_directory(Path(tool_path), recursive)
                else:
                    logger.warning(f"Unknown tool type: {tool_type}")
                    continue
                
                count += loaded
                logger.info(f"Loaded {loaded} tools from {tool_type}: {tool_path}")
                
            except Exception as e:
                logger.error(f"Error loading {tool_type} {tool_path}: {e}")
        
        return count
    
    def load_builtin_tools(self) -> int:
        """Load all built-in tools."""
        try:
            from . import builtin
            return self.registry.discover_tools('src.tools.builtin')
        except Exception as e:
            logger.error(f"Error loading built-in tools: {e}")
            return 0
    
    def create_tool_from_function(self, func, **kwargs) -> Tool:
        """Create a tool from a function using the @tool decorator.
        
        Args:
            func: Function to convert to tool
            **kwargs: Arguments for @tool decorator
        
        Returns:
            Tool instance
        """
        from .decorators import tool
        
        # Apply decorator
        decorated = tool(**kwargs)(func)
        
        # Return the tool instance
        return decorated.tool
    
    def reload_tool(self, tool_name: str) -> bool:
        """Reload a tool by re-importing its module.
        
        Args:
            tool_name: Name of tool to reload
        
        Returns:
            True if successful
        """
        tool = self.registry.get(tool_name)
        if not tool:
            return False
        
        # Find the module containing the tool
        tool_module = sys.modules.get(tool.__class__.__module__)
        if not tool_module:
            return False
        
        try:
            # Reload the module
            importlib.reload(tool_module)
            
            # Re-register tools from module
            self.registry._register_tools_from_module(tool_module)
            
            return True
            
        except Exception as e:
            logger.error(f"Error reloading tool {tool_name}: {e}")
            return False
    
    def unload_module(self, module_path: str) -> int:
        """Unload all tools from a module.
        
        Args:
            module_path: Path to module that was loaded
        
        Returns:
            Number of tools unloaded
        """
        if module_path not in self.loaded_modules:
            return 0
        
        module = self.loaded_modules[module_path]
        count = 0
        
        # Find and unregister all tools from this module
        for tool in list(self.registry.list_tools()):
            if tool.__class__.__module__ == module.__name__:
                if self.registry.unregister(tool.name):
                    count += 1
        
        # Remove module
        del self.loaded_modules[module_path]
        if module.__name__ in sys.modules:
            del sys.modules[module.__name__]
        
        return count


class ToolDiscovery:
    """Automatic tool discovery from environment."""
    
    def __init__(self, loader: Optional[ToolLoader] = None):
        self.loader = loader or ToolLoader()
        self.search_paths: List[Path] = []
        self._setup_default_paths()
    
    def _setup_default_paths(self):
        """Setup default search paths for tools."""
        # Current directory tools/ folder
        self.search_paths.append(Path.cwd() / "tools")
        
        # User home .ajentik/tools/
        home_tools = Path.home() / ".ajentik" / "tools"
        self.search_paths.append(home_tools)
        
        # Environment variable paths
        env_paths = os.environ.get("AJENTIK_TOOL_PATH", "").split(":")
        for path in env_paths:
            if path:
                self.search_paths.append(Path(path))
    
    def add_search_path(self, path: Path):
        """Add a search path for tool discovery."""
        path = Path(path).resolve()
        if path not in self.search_paths:
            self.search_paths.append(path)
    
    def discover_all(self) -> Dict[str, int]:
        """Discover tools from all search paths.
        
        Returns:
            Dictionary mapping paths to number of tools loaded
        """
        results = {}
        
        # Load built-in tools first
        builtin_count = self.loader.load_builtin_tools()
        results["builtin"] = builtin_count
        
        # Search all paths
        for search_path in self.search_paths:
            if search_path.exists() and search_path.is_dir():
                try:
                    count = self.loader.load_from_directory(search_path)
                    results[str(search_path)] = count
                    logger.info(f"Discovered {count} tools from {search_path}")
                except Exception as e:
                    logger.error(f"Error discovering tools from {search_path}: {e}")
                    results[str(search_path)] = 0
        
        # Look for tool config files
        for config_name in ["tools.yaml", "tools.yml", "tools.json", ".ajentik-tools.yaml"]:
            config_path = Path.cwd() / config_name
            if config_path.exists():
                try:
                    count = self.loader.load_from_config(config_path)
                    results[str(config_path)] = count
                    logger.info(f"Loaded {count} tools from config {config_path}")
                except Exception as e:
                    logger.error(f"Error loading config {config_path}: {e}")
        
        return results
    
    def watch_for_changes(self, callback=None):
        """Watch tool directories for changes and reload automatically.
        
        Args:
            callback: Function to call when tools are reloaded
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class ToolFileHandler(FileSystemEventHandler):
                def __init__(self, discovery, callback):
                    self.discovery = discovery
                    self.callback = callback
                
                def on_modified(self, event):
                    if event.src_path.endswith('.py'):
                        logger.info(f"Tool file modified: {event.src_path}")
                        # Reload tools
                        self.discovery.discover_all()
                        if self.callback:
                            self.callback()
            
            handler = ToolFileHandler(self, callback)
            observer = Observer()
            
            for path in self.search_paths:
                if path.exists():
                    observer.schedule(handler, str(path), recursive=True)
            
            observer.start()
            logger.info("Started watching for tool changes")
            
            return observer
            
        except ImportError:
            logger.warning("watchdog not installed, cannot watch for changes")
            return None


# Global instances
tool_loader = ToolLoader()
tool_discovery = ToolDiscovery(tool_loader)