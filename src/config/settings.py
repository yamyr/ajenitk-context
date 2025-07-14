"""Application settings using Pydantic."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from functools import lru_cache

from pydantic import BaseSettings, Field, validator
from pydantic.types import SecretStr

from ..tools.registry_refactored import SecurityLevel


class MCPSettings(BaseSettings):
    """MCP-specific settings."""
    
    timeout: int = Field(30, description="MCP request timeout in seconds")
    max_message_size: int = Field(1048576, description="Maximum message size in bytes")
    protocol_version: str = Field("2024-11-05", description="MCP protocol version")
    
    class Config:
        env_prefix = "AJENTIK_MCP_"


class ToolSettings(BaseSettings):
    """Tool system settings."""
    
    security_level: SecurityLevel = Field(
        SecurityLevel.SAFE,
        description="Default security level for tool execution"
    )
    discovery_paths: List[str] = Field(
        default_factory=list,
        description="Paths to discover tools from"
    )
    max_execution_time: float = Field(
        300.0,
        description="Maximum tool execution time in seconds"
    )
    enable_statistics: bool = Field(
        True,
        description="Enable execution statistics tracking"
    )
    
    @validator('discovery_paths', pre=True)
    def parse_discovery_paths(cls, v):
        """Parse comma-separated paths."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(',') if p.strip()]
        return v
    
    class Config:
        env_prefix = "AJENTIK_TOOLS_"


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: str = Field("INFO", description="Log level")
    format: str = Field("text", description="Log format (text, json)")
    file: Optional[Path] = Field(None, description="Log file path")
    enable_colors: bool = Field(True, description="Enable colored output")
    
    @validator('level')
    def validate_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()
    
    class Config:
        env_prefix = "AJENTIK_LOG_"


class DatabaseSettings(BaseSettings):
    """Database settings for persistence."""
    
    url: Optional[str] = Field(None, description="Database URL")
    pool_size: int = Field(5, description="Connection pool size")
    max_overflow: int = Field(10, description="Maximum overflow connections")
    
    class Config:
        env_prefix = "AJENTIK_DB_"


class APISettings(BaseSettings):
    """API server settings."""
    
    host: str = Field("127.0.0.1", description="API host")
    port: int = Field(8000, description="API port")
    cors_origins: List[str] = Field(
        ["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    api_key: Optional[SecretStr] = Field(None, description="API key for authentication")
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated origins."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(',') if o.strip()]
        return v
    
    class Config:
        env_prefix = "AJENTIK_API_"


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application info
    app_name: str = Field("Ajentik", description="Application name")
    version: str = Field("0.1.0", description="Application version")
    environment: str = Field("development", description="Environment (development, staging, production)")
    debug: bool = Field(False, description="Debug mode")
    
    # Paths
    data_dir: Path = Field(
        Path.home() / ".ajentik",
        description="Data directory"
    )
    config_dir: Path = Field(
        Path.home() / ".config" / "ajentik",
        description="Configuration directory"
    )
    cache_dir: Path = Field(
        Path.home() / ".cache" / "ajentik",
        description="Cache directory"
    )
    
    # Sub-configurations
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    
    # Feature flags
    features: Dict[str, bool] = Field(
        default_factory=lambda: {
            "mcp_server": True,
            "mcp_client": True,
            "api_server": False,
            "web_ui": False,
            "telemetry": False,
        },
        description="Feature flags"
    )
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Invalid environment: {v}")
        return v
    
    def setup_directories(self):
        """Create necessary directories."""
        for dir_path in [self.data_dir, self.config_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with secrets hidden."""
        data = self.dict()
        # Hide sensitive values
        if self.api.api_key:
            data['api']['api_key'] = "***"
        return data
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Allow extra fields for extensibility
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.setup_directories()
    return settings