"""Configuration models for the ajentik system."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .schemas import ModelProvider


class LogfireConfig(BaseModel):
    """Logfire monitoring configuration."""
    enabled: bool = True
    project: str = "ajenitk-context"
    service_name: str = "ajentik-ai"
    console: bool = True
    write_token: Optional[SecretStr] = None
    export_to_otlp: bool = False
    otlp_endpoint: Optional[str] = None


class ModelConfig(BaseModel):
    """Model provider configuration."""
    provider: ModelProvider
    model_name: str
    api_key: Optional[SecretStr] = None
    base_url: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    timeout: int = Field(default=60, gt=0)
    
    @property
    def model_string(self) -> str:
        """Get the model string in provider:model format."""
        return f"{self.provider.value}:{self.model_name}"


class AgentSystemConfig(BaseModel):
    """System-wide agent configuration."""
    default_model: str = "openai:gpt-4o"
    fallback_models: List[str] = ["anthropic:claude-3-5-sonnet"]
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, ge=0.0)
    enable_caching: bool = True
    cache_ttl_seconds: int = Field(default=3600, gt=0)
    max_context_length: int = Field(default=100000, gt=0)
    enable_streaming: bool = True
    
    @field_validator("fallback_models")
    def validate_fallback_models(cls, v: List[str]) -> List[str]:
        """Validate fallback model formats."""
        for model in v:
            if ":" not in model:
                raise ValueError(f"Model must be in format 'provider:model_name': {model}")
        return v


class CLIConfig(BaseModel):
    """CLI interface configuration."""
    color_theme: str = "monokai"
    history_file: Path = Path.home() / ".ajentik_history"
    history_size: int = Field(default=1000, gt=0)
    auto_save: bool = True
    show_timestamps: bool = True
    enable_syntax_highlighting: bool = True
    enable_markdown_rendering: bool = True
    spinner_style: str = "dots"


class SecurityConfig(BaseModel):
    """Security and safety configuration."""
    enable_content_filtering: bool = True
    enable_prompt_injection_detection: bool = True
    allowed_file_extensions: List[str] = [
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go",
        ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
        ".md", ".txt", ".json", ".yaml", ".yml", ".toml"
    ]
    max_file_size_mb: int = Field(default=10, gt=0)
    sandbox_code_execution: bool = True
    require_confirmation_for_destructive: bool = True


class Settings(BaseSettings):
    """Main application settings loaded from environment."""
    # API Keys
    openai_api_key: Optional[SecretStr] = None
    anthropic_api_key: Optional[SecretStr] = None
    google_api_key: Optional[SecretStr] = None
    groq_api_key: Optional[SecretStr] = None
    cohere_api_key: Optional[SecretStr] = None
    mistral_api_key: Optional[SecretStr] = None
    
    # Logfire
    logfire_project: str = "ajenitk-context"
    logfire_write_token: Optional[SecretStr] = None
    logfire_service_name: str = "ajentik-ai"
    logfire_console: bool = True
    
    # Agent System
    default_model: str = "openai:gpt-4o"
    fallback_model: str = "anthropic:claude-3-5-sonnet"
    max_retries: int = 3
    timeout_seconds: int = 60
    temperature: float = 0.7
    
    # CLI
    cli_color_theme: str = "monokai"
    cli_history_file: str = "~/.ajentik_history"
    
    # Security
    enable_sandboxing: bool = True
    max_file_size_mb: int = 10
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    def get_model_config(self, provider: ModelProvider) -> Optional[ModelConfig]:
        """Get model configuration for a specific provider."""
        api_key_map = {
            ModelProvider.OPENAI: self.openai_api_key,
            ModelProvider.ANTHROPIC: self.anthropic_api_key,
            ModelProvider.GOOGLE: self.google_api_key,
            ModelProvider.GROQ: self.groq_api_key,
            ModelProvider.COHERE: self.cohere_api_key,
            ModelProvider.MISTRAL: self.mistral_api_key,
        }
        
        api_key = api_key_map.get(provider)
        if not api_key:
            return None
            
        return ModelConfig(
            provider=provider,
            model_name=self.default_model.split(":", 1)[1] if ":" in self.default_model else "gpt-4o",
            api_key=api_key,
            temperature=self.temperature,
            timeout=self.timeout_seconds
        )
    
    def get_logfire_config(self) -> LogfireConfig:
        """Get Logfire configuration."""
        return LogfireConfig(
            project=self.logfire_project,
            service_name=self.logfire_service_name,
            console=self.logfire_console,
            write_token=self.logfire_write_token
        )
    
    def get_agent_system_config(self) -> AgentSystemConfig:
        """Get agent system configuration."""
        fallback_models = [self.fallback_model] if self.fallback_model else []
        return AgentSystemConfig(
            default_model=self.default_model,
            fallback_models=fallback_models,
            max_retries=self.max_retries
        )
    
    def get_cli_config(self) -> CLIConfig:
        """Get CLI configuration."""
        return CLIConfig(
            color_theme=self.cli_color_theme,
            history_file=Path(os.path.expanduser(self.cli_history_file))
        )
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return SecurityConfig(
            sandbox_code_execution=self.enable_sandboxing,
            max_file_size_mb=self.max_file_size_mb
        )