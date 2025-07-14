"""Configuration loader with multiple sources."""

import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ConfigSource(ABC):
    """Abstract base class for configuration sources."""
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Load configuration from source."""
        pass
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if source exists."""
        pass


class JSONConfigSource(ConfigSource):
    """JSON file configuration source."""
    
    def __init__(self, path: Path):
        self.path = path
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON config from {self.path}: {e}")
            return {}
    
    def exists(self) -> bool:
        """Check if JSON file exists."""
        return self.path.exists()


class YAMLConfigSource(ConfigSource):
    """YAML file configuration source."""
    
    def __init__(self, path: Path):
        self.path = path
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load YAML config from {self.path}: {e}")
            return {}
    
    def exists(self) -> bool:
        """Check if YAML file exists."""
        return self.path.exists()


class EnvironmentConfigSource(ConfigSource):
    """Environment variables configuration source."""
    
    def __init__(self, prefix: str = "AJENTIK_"):
        self.prefix = prefix
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(self.prefix):].lower()
                
                # Convert underscores to dots for nested config
                config_key = config_key.replace('_', '.')
                
                # Parse value
                parsed_value = self._parse_value(value)
                
                # Set nested value
                self._set_nested(config, config_key, parsed_value)
        
        return config
    
    def exists(self) -> bool:
        """Environment always exists."""
        return True
    
    def _parse_value(self, value: str) -> Any:
        """Parse environment variable value."""
        # Try to parse as JSON
        try:
            return json.loads(value)
        except:
            pass
        
        # Try to parse as boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except:
            pass
        
        # Return as string
        return value
    
    def _set_nested(self, config: Dict[str, Any], key: str, value: Any):
        """Set nested configuration value."""
        parts = key.split('.')
        current = config
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value


class ConfigLoader:
    """Configuration loader that merges multiple sources."""
    
    def __init__(self):
        self.sources: List[ConfigSource] = []
        self._config: Optional[Dict[str, Any]] = None
    
    def add_source(self, source: ConfigSource) -> 'ConfigLoader':
        """Add a configuration source."""
        self.sources.append(source)
        return self
    
    def add_json_file(self, path: Path) -> 'ConfigLoader':
        """Add JSON file source."""
        return self.add_source(JSONConfigSource(path))
    
    def add_yaml_file(self, path: Path) -> 'ConfigLoader':
        """Add YAML file source."""
        return self.add_source(YAMLConfigSource(path))
    
    def add_environment(self, prefix: str = "AJENTIK_") -> 'ConfigLoader':
        """Add environment variables source."""
        return self.add_source(EnvironmentConfigSource(prefix))
    
    def load(self, reload: bool = False) -> Dict[str, Any]:
        """Load and merge configuration from all sources."""
        if self._config is not None and not reload:
            return self._config
        
        config = {}
        
        for source in self.sources:
            if source.exists():
                source_config = source.load()
                if source_config:
                    config = self._deep_merge(config, source_config)
                    logger.debug(f"Loaded config from {source.__class__.__name__}")
        
        self._config = config
        return config
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        if self._config is None:
            self.load()
        
        parts = key.split('.')
        current = self._config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any):
        """Set configuration value by dot-separated key."""
        if self._config is None:
            self.load()
        
        parts = key.split('.')
        current = self._config
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    @classmethod
    def default(cls) -> 'ConfigLoader':
        """Create default configuration loader."""
        from .settings import get_settings
        settings = get_settings()
        
        loader = cls()
        
        # Add default sources
        loader.add_json_file(settings.config_dir / "config.json")
        loader.add_yaml_file(settings.config_dir / "config.yaml")
        loader.add_json_file(Path.cwd() / ".ajentik.json")
        loader.add_yaml_file(Path.cwd() / ".ajentik.yaml")
        loader.add_environment()
        
        return loader