"""Tests for data models and schemas."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models import (
    # Configs
    AgentConfig,
    ModelProvider,
    LogfireConfig,
    Settings,
    
    # Schemas
    Message,
    MessageRole,
    ConversationHistory,
    ChatResponse,
    CodeGenerationRequest,
    CodeGenerationResponse,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeIssue,
    IssueSeverity,
    ToolResult,
    AgentMetrics
)


class TestAgentConfig:
    """Test AgentConfig model."""
    
    def test_agent_config_defaults(self):
        """Test default values for AgentConfig."""
        config = AgentConfig(name="TestAgent")
        
        assert config.name == "TestAgent"
        assert config.model == "openai:gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.system_message is None
    
    def test_agent_config_custom_values(self):
        """Test custom values for AgentConfig."""
        config = AgentConfig(
            name="CustomAgent",
            model="anthropic:claude-3-5-sonnet",
            temperature=0.5,
            max_tokens=2000,
            timeout=60.0,
            max_retries=5,
            system_message="You are a custom assistant."
        )
        
        assert config.model == "anthropic:claude-3-5-sonnet"
        assert config.temperature == 0.5
        assert config.system_message == "You are a custom assistant."
    
    def test_agent_config_validation(self):
        """Test validation for AgentConfig."""
        # Temperature must be between 0 and 2
        with pytest.raises(ValidationError):
            AgentConfig(name="Test", temperature=3.0)
        
        # Max tokens must be positive
        with pytest.raises(ValidationError):
            AgentConfig(name="Test", max_tokens=-100)
        
        # Timeout must be positive
        with pytest.raises(ValidationError):
            AgentConfig(name="Test", timeout=0)


class TestSettings:
    """Test Settings model."""
    
    def test_settings_from_env(self, mock_env):
        """Test loading settings from environment."""
        settings = Settings()
        
        assert settings.openai_api_key.get_secret_value() == "test-openai-key"
        assert settings.anthropic_api_key.get_secret_value() == "test-anthropic-key"
        assert settings.google_api_key.get_secret_value() == "test-google-key"
    
    def test_settings_defaults(self, mock_env):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.default_model == "openai:gpt-4o"
        assert settings.default_temperature == 0.7
        assert settings.default_max_tokens == 1000
        assert settings.enable_monitoring is True
    
    def test_get_model_provider(self, mock_env):
        """Test getting model provider from settings."""
        settings = Settings()
        
        assert settings.get_model_provider("openai:gpt-4") == ModelProvider.OPENAI
        assert settings.get_model_provider("anthropic:claude") == ModelProvider.ANTHROPIC
        assert settings.get_model_provider("google:gemini") == ModelProvider.GOOGLE
        assert settings.get_model_provider("unknown:model") == ModelProvider.OPENAI  # Default
    
    def test_get_logfire_config(self, mock_env):
        """Test getting Logfire configuration."""
        settings = Settings()
        config = settings.get_logfire_config()
        
        assert isinstance(config, LogfireConfig)
        assert config.project == "test-project"
        assert config.write_token.get_secret_value() == "test-logfire-token"


class TestMessage:
    """Test Message model."""
    
    def test_message_creation(self):
        """Test creating messages."""
        msg = Message(
            role=MessageRole.USER,
            content="Hello, assistant!"
        )
        
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello, assistant!"
    
    def test_message_roles(self):
        """Test different message roles."""
        user_msg = Message(role=MessageRole.USER, content="User message")
        assistant_msg = Message(role=MessageRole.ASSISTANT, content="Assistant message")
        system_msg = Message(role=MessageRole.SYSTEM, content="System message")
        
        assert user_msg.role.value == "user"
        assert assistant_msg.role.value == "assistant"
        assert system_msg.role.value == "system"


class TestConversationHistory:
    """Test ConversationHistory model."""
    
    def test_conversation_history_creation(self):
        """Test creating conversation history."""
        history = ConversationHistory(
            messages=[
                Message(role=MessageRole.USER, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi there!")
            ],
            session_id="test-123"
        )
        
        assert len(history.messages) == 2
        assert history.session_id == "test-123"
        assert history.metadata == {}
    
    def test_conversation_history_with_metadata(self):
        """Test conversation history with metadata."""
        history = ConversationHistory(
            messages=[],
            session_id="test-456",
            metadata={"user_id": "user123", "topic": "python"}
        )
        
        assert history.metadata["user_id"] == "user123"
        assert history.metadata["topic"] == "python"


class TestChatResponse:
    """Test ChatResponse model."""
    
    def test_chat_response_basic(self):
        """Test basic chat response."""
        response = ChatResponse(
            message="I can help with that!",
            confidence=0.95
        )
        
        assert response.message == "I can help with that!"
        assert response.confidence == 0.95
        assert response.suggested_actions is None
    
    def test_chat_response_with_suggestions(self):
        """Test chat response with suggested actions."""
        response = ChatResponse(
            message="Here's your answer",
            confidence=0.8,
            suggested_actions=["Ask for clarification", "Request an example"]
        )
        
        assert len(response.suggested_actions) == 2
        assert "Ask for clarification" in response.suggested_actions


class TestCodeGeneration:
    """Test code generation models."""
    
    def test_code_generation_request_basic(self):
        """Test basic code generation request."""
        request = CodeGenerationRequest(
            description="Create a sorting function",
            language="python"
        )
        
        assert request.description == "Create a sorting function"
        assert request.language == "python"
        assert request.framework is None
        assert request.requirements is None
    
    def test_code_generation_request_full(self):
        """Test full code generation request."""
        request = CodeGenerationRequest(
            description="Create a REST API",
            language="python",
            framework="fastapi",
            requirements=["Include authentication", "Add CORS support"],
            constraints=["Use async functions", "Follow PEP 8"],
            examples=["GET /users", "POST /login"]
        )
        
        assert request.framework == "fastapi"
        assert len(request.requirements) == 2
        assert len(request.constraints) == 2
        assert len(request.examples) == 1
    
    def test_code_generation_response(self):
        """Test code generation response."""
        response = CodeGenerationResponse(
            code="def sort_list(lst):\n    return sorted(lst)",
            language="python",
            framework=None,
            explanation="Simple sorting function using Python's built-in sorted()",
            dependencies=["No external dependencies"],
            warnings=["Consider handling None values"]
        )
        
        assert "def sort_list" in response.code
        assert response.explanation is not None
        assert len(response.warnings) == 1


class TestCodeAnalysis:
    """Test code analysis models."""
    
    def test_code_analysis_request(self):
        """Test code analysis request."""
        request = CodeAnalysisRequest(
            code="print('hello')",
            language="python",
            analysis_types=["quality", "security"],
            include_suggestions=True,
            context="CLI script"
        )
        
        assert request.code == "print('hello')"
        assert "quality" in request.analysis_types
        assert request.include_suggestions is True
    
    def test_code_issue(self):
        """Test code issue model."""
        issue = CodeIssue(
            type="security",
            severity=IssueSeverity.HIGH,
            description="Hardcoded password detected",
            line_number=42,
            column_number=10,
            suggestion="Use environment variables instead"
        )
        
        assert issue.type == "security"
        assert issue.severity == IssueSeverity.HIGH
        assert issue.line_number == 42
        assert issue.suggestion is not None
    
    def test_code_analysis_response(self):
        """Test code analysis response."""
        response = CodeAnalysisResponse(
            summary="Code has security vulnerabilities",
            issues=[
                CodeIssue(
                    type="security",
                    severity=IssueSeverity.HIGH,
                    description="SQL injection vulnerability"
                )
            ],
            overall_score=4.5,
            metrics={"lines": 100, "complexity": 15},
            suggestions=["Use parameterized queries"],
            security_score=2.0,
            quality_score=6.0,
            performance_score=7.0
        )
        
        assert response.overall_score == 4.5
        assert len(response.issues) == 1
        assert response.security_score == 2.0


class TestToolResult:
    """Test ToolResult model."""
    
    def test_tool_result_success(self):
        """Test successful tool result."""
        result = ToolResult(
            tool_name="file_reader",
            success=True,
            output="File contents here",
            execution_time=0.25
        )
        
        assert result.success is True
        assert result.output == "File contents here"
        assert result.error is None
    
    def test_tool_result_failure(self):
        """Test failed tool result."""
        result = ToolResult(
            tool_name="web_search",
            success=False,
            output="",
            execution_time=5.0,
            error="Connection timeout"
        )
        
        assert result.success is False
        assert result.error == "Connection timeout"


class TestAgentMetrics:
    """Test AgentMetrics model."""
    
    def test_agent_metrics_defaults(self):
        """Test default agent metrics."""
        metrics = AgentMetrics()
        
        assert metrics.agent_name == "unknown"
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.average_response_time == 0.0
        assert metrics.total_tokens_used == 0
        assert metrics.total_cost == 0.0
    
    def test_agent_metrics_success_rate(self):
        """Test success rate calculation."""
        metrics = AgentMetrics(
            agent_name="TestAgent",
            total_requests=10,
            successful_requests=8,
            failed_requests=2
        )
        
        assert metrics.success_rate == 80.0
    
    def test_agent_metrics_no_requests(self):
        """Test success rate with no requests."""
        metrics = AgentMetrics()
        assert metrics.success_rate == 0.0


class TestModelSerialization:
    """Test model serialization/deserialization."""
    
    def test_conversation_history_json(self):
        """Test JSON serialization of conversation history."""
        history = ConversationHistory(
            messages=[
                Message(role=MessageRole.USER, content="Hello"),
                Message(role=MessageRole.ASSISTANT, content="Hi!")
            ],
            session_id="json-test"
        )
        
        # Serialize to JSON
        json_str = json.dumps(history.dict())
        
        # Deserialize from JSON
        data = json.loads(json_str)
        restored = ConversationHistory(**data)
        
        assert len(restored.messages) == 2
        assert restored.session_id == "json-test"
    
    def test_agent_config_dict(self):
        """Test dictionary conversion of agent config."""
        config = AgentConfig(
            name="DictTest",
            temperature=0.5,
            system_message="Test message"
        )
        
        config_dict = config.dict()
        
        assert config_dict["name"] == "DictTest"
        assert config_dict["temperature"] == 0.5
        assert config_dict["system_message"] == "Test message"
        
        # Recreate from dict
        new_config = AgentConfig(**config_dict)
        assert new_config.name == config.name
        assert new_config.temperature == config.temperature