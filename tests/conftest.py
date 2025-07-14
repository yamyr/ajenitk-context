"""Pytest configuration and shared fixtures."""

import asyncio
import os
from pathlib import Path
from typing import Generator, AsyncGenerator

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock

from src.models import (
    AgentConfig,
    ConversationHistory,
    Message,
    MessageRole,
    Settings
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "GOOGLE_API_KEY": "test-google-key",
        "LOGFIRE_WRITE_TOKEN": "test-logfire-token",
        "LOGFIRE_PROJECT": "test-project"
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        openai_api_key="test-openai-key",
        default_model="openai:gpt-4",
        default_temperature=0.7,
        default_max_tokens=1000,
        log_level="INFO",
        enable_monitoring=True
    )


@pytest.fixture
def sample_agent_config():
    """Create a sample agent configuration."""
    return AgentConfig(
        name="TestAgent",
        model="openai:gpt-4",
        temperature=0.5,
        max_tokens=500,
        timeout=10.0,
        max_retries=2,
        system_message="You are a test assistant."
    )


@pytest.fixture
def sample_conversation_history():
    """Create a sample conversation history."""
    return ConversationHistory(
        messages=[
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi! How can I help you?"),
            Message(role=MessageRole.USER, content="What's Python?"),
            Message(role=MessageRole.ASSISTANT, content="Python is a programming language.")
        ],
        session_id="test-session-123",
        metadata={"test": True}
    )


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return """
def calculate_factorial(n):
    \"\"\"Calculate factorial of n.\"\"\"
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    elif n == 0:
        return 1
    else:
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result

def main():
    print(calculate_factorial(5))

if __name__ == "__main__":
    main()
"""


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return """
function fibonacci(n) {
    if (n <= 1) return n;
    
    let prev = 0;
    let curr = 1;
    
    for (let i = 2; i <= n; i++) {
        const temp = curr;
        curr = prev + curr;
        prev = temp;
    }
    
    return curr;
}

console.log(fibonacci(10));
"""


@pytest.fixture
def mock_pydantic_agent():
    """Create a mock PydanticAI agent."""
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock()
    mock_agent.run_sync = MagicMock()
    
    # Mock response
    mock_response = MagicMock()
    mock_response.data = MagicMock()
    mock_response.usage = MagicMock(return_value=MagicMock(total_tokens=100))
    
    mock_agent.run.return_value = mock_response
    mock_agent.run_sync.return_value = mock_response
    
    return mock_agent


@pytest_asyncio.fixture
async def mock_logfire():
    """Mock Logfire for testing."""
    with pytest.MonkeyPatch.context() as mp:
        mock_logfire = MagicMock()
        mock_logfire.info = MagicMock()
        mock_logfire.error = MagicMock()
        mock_logfire.warning = MagicMock()
        mock_logfire.span = MagicMock()
        mock_logfire.configure = MagicMock()
        mock_logfire.instrument_pydantic_ai = MagicMock()
        
        mp.setattr("src.utils.logfire_setup.logfire", mock_logfire)
        mp.setattr("src.monitoring.enhanced_monitoring.logfire", mock_logfire)
        
        yield mock_logfire


@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner."""
    from click.testing import CliRunner
    return CliRunner()