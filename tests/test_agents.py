"""Tests for agent implementations."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.agents import ChatAgent, CodeAgent, AnalysisAgent
from src.models import (
    ChatResponse,
    CodeGenerationRequest,
    CodeGenerationResponse,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeIssue,
    ConversationHistory
)


class TestChatAgent:
    """Tests for ChatAgent."""
    
    @pytest.mark.asyncio
    async def test_chat_basic(self, sample_agent_config, mock_pydantic_agent):
        """Test basic chat functionality."""
        # Mock the response
        mock_response_data = ChatResponse(
            message="Hello! I can help you with that.",
            confidence=0.95,
            suggested_actions=["Ask a follow-up question"]
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        # Create agent with mocked PydanticAI agent
        with patch('src.agents.chat_agent.Agent', return_value=mock_pydantic_agent):
            agent = ChatAgent(sample_agent_config)
            
            # Test chat
            response = await agent.chat(
                "Hello, can you help me?",
                ConversationHistory(messages=[], session_id="test")
            )
            
            assert response.message == "Hello! I can help you with that."
            assert response.confidence == 0.95
            assert len(response.suggested_actions) == 1
    
    @pytest.mark.asyncio
    async def test_chat_with_history(self, sample_conversation_history, mock_pydantic_agent):
        """Test chat with conversation history."""
        mock_response_data = ChatResponse(
            message="Based on our previous discussion about Python...",
            confidence=0.9
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.chat_agent.Agent', return_value=mock_pydantic_agent):
            agent = ChatAgent()
            
            response = await agent.chat(
                "Tell me more about that",
                sample_conversation_history
            )
            
            # Verify history was passed
            assert mock_pydantic_agent.run.called
            call_args = mock_pydantic_agent.run.call_args
            assert "Previous conversation:" in call_args[0][0]
    
    def test_chat_sync(self, mock_pydantic_agent):
        """Test synchronous chat."""
        mock_response_data = ChatResponse(
            message="Sync response",
            confidence=0.85
        )
        mock_pydantic_agent.run_sync.return_value.data = mock_response_data
        
        with patch('src.agents.chat_agent.Agent', return_value=mock_pydantic_agent):
            agent = ChatAgent()
            
            response = agent.chat_sync(
                "Test sync",
                ConversationHistory(messages=[], session_id="sync-test")
            )
            
            assert response.message == "Sync response"
            assert mock_pydantic_agent.run_sync.called


class TestCodeAgent:
    """Tests for CodeAgent."""
    
    @pytest.mark.asyncio
    async def test_generate_code_basic(self, mock_pydantic_agent):
        """Test basic code generation."""
        mock_response_data = CodeGenerationResponse(
            code="def hello():\n    print('Hello, World!')",
            language="python",
            explanation="A simple hello world function",
            dependencies=["None required"],
            warnings=[]
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.code_agent.Agent', return_value=mock_pydantic_agent):
            agent = CodeAgent()
            
            request = CodeGenerationRequest(
                description="Create a hello world function",
                language="python"
            )
            
            response = await agent.generate_code(request)
            
            assert "def hello():" in response.code
            assert response.language == "python"
            assert response.explanation is not None
    
    @pytest.mark.asyncio
    async def test_generate_code_with_requirements(self, mock_pydantic_agent):
        """Test code generation with specific requirements."""
        mock_response_data = CodeGenerationResponse(
            code="from typing import List\n\ndef process_data(data: List[int]) -> int:\n    return sum(data)",
            language="python",
            framework=None,
            explanation="Function with type hints as requested"
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.code_agent.Agent', return_value=mock_pydantic_agent):
            agent = CodeAgent()
            
            request = CodeGenerationRequest(
                description="Create a data processing function",
                language="python",
                requirements=["Use type hints", "Handle lists of integers"]
            )
            
            response = await agent.generate_code(request)
            
            assert "typing" in response.code
            assert "List[int]" in response.code
    
    @pytest.mark.asyncio
    async def test_generate_code_with_framework(self, mock_pydantic_agent):
        """Test code generation with framework specification."""
        mock_response_data = CodeGenerationResponse(
            code="import React from 'react';\n\nconst App = () => {\n  return <div>Hello</div>;\n};",
            language="javascript",
            framework="react",
            dependencies=["react", "react-dom"]
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.code_agent.Agent', return_value=mock_pydantic_agent):
            agent = CodeAgent()
            
            request = CodeGenerationRequest(
                description="Create a React component",
                language="javascript",
                framework="react"
            )
            
            response = await agent.generate_code(request)
            
            assert response.framework == "react"
            assert "react" in response.dependencies


class TestAnalysisAgent:
    """Tests for AnalysisAgent."""
    
    @pytest.mark.asyncio
    async def test_analyze_code_basic(self, sample_python_code, mock_pydantic_agent):
        """Test basic code analysis."""
        mock_response_data = CodeAnalysisResponse(
            summary="Code is well-structured with proper error handling",
            issues=[
                CodeIssue(
                    type="style",
                    severity="low",
                    description="Consider using f-strings",
                    line_number=15,
                    suggestion="Use f-string for better readability"
                )
            ],
            overall_score=8.5,
            metrics={"lines": 20, "complexity": 3}
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.analysis_agent.Agent', return_value=mock_pydantic_agent):
            agent = AnalysisAgent()
            
            request = CodeAnalysisRequest(
                code=sample_python_code,
                language="python",
                analysis_types=["quality"]
            )
            
            response = await agent.analyze_code(request)
            
            assert response.overall_score == 8.5
            assert len(response.issues) == 1
            assert response.issues[0].severity == "low"
            assert "metrics" in response.__dict__ and response.metrics is not None
    
    @pytest.mark.asyncio
    async def test_analyze_code_security(self, mock_pydantic_agent):
        """Test security analysis."""
        insecure_code = """
import os
password = "hardcoded_password"
os.system(f"echo {user_input}")  # Command injection
"""
        
        mock_response_data = CodeAnalysisResponse(
            summary="Critical security vulnerabilities found",
            issues=[
                CodeIssue(
                    type="security",
                    severity="high",
                    description="Hardcoded password detected",
                    line_number=2,
                    suggestion="Use environment variables for sensitive data"
                ),
                CodeIssue(
                    type="security",
                    severity="high",
                    description="Potential command injection vulnerability",
                    line_number=3,
                    suggestion="Use subprocess with proper escaping"
                )
            ],
            overall_score=3.0,
            security_score=2.0
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.analysis_agent.Agent', return_value=mock_pydantic_agent):
            agent = AnalysisAgent()
            
            request = CodeAnalysisRequest(
                code=insecure_code,
                language="python",
                analysis_types=["security"]
            )
            
            response = await agent.analyze_code(request)
            
            assert response.overall_score == 3.0
            assert len(response.issues) == 2
            assert all(issue.type == "security" for issue in response.issues)
            assert all(issue.severity == "high" for issue in response.issues)
    
    @pytest.mark.asyncio
    async def test_analyze_code_with_suggestions(self, sample_javascript_code, mock_pydantic_agent):
        """Test analysis with improvement suggestions."""
        mock_response_data = CodeAnalysisResponse(
            summary="Code is functional but could be optimized",
            issues=[],
            suggestions=[
                "Consider memoization for recursive calls",
                "Add input validation",
                "Include JSDoc comments"
            ],
            overall_score=7.0
        )
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.analysis_agent.Agent', return_value=mock_pydantic_agent):
            agent = AnalysisAgent()
            
            request = CodeAnalysisRequest(
                code=sample_javascript_code,
                language="javascript",
                analysis_types=["quality", "performance"],
                include_suggestions=True
            )
            
            response = await agent.analyze_code(request)
            
            assert response.suggestions is not None
            assert len(response.suggestions) == 3
            assert "memoization" in response.suggestions[0]


class TestAgentIntegration:
    """Integration tests for agents working together."""
    
    @pytest.mark.asyncio
    async def test_chat_to_code_workflow(self, mock_pydantic_agent):
        """Test workflow from chat to code generation."""
        # Mock chat response suggesting code generation
        chat_response = ChatResponse(
            message="I'll help you create that function",
            confidence=0.95,
            suggested_actions=["Generate Python function for sorting"]
        )
        
        # Mock code generation response
        code_response = CodeGenerationResponse(
            code="def sort_list(lst):\n    return sorted(lst)",
            language="python",
            explanation="Simple sorting function"
        )
        
        with patch('src.agents.chat_agent.Agent', return_value=mock_pydantic_agent):
            with patch('src.agents.code_agent.Agent', return_value=mock_pydantic_agent):
                # First, chat interaction
                mock_pydantic_agent.run.return_value.data = chat_response
                chat_agent = ChatAgent()
                chat_result = await chat_agent.chat(
                    "I need a sorting function",
                    ConversationHistory(messages=[], session_id="workflow-test")
                )
                
                # Then, code generation based on suggestion
                mock_pydantic_agent.run.return_value.data = code_response
                code_agent = CodeAgent()
                code_request = CodeGenerationRequest(
                    description=chat_result.suggested_actions[0],
                    language="python"
                )
                code_result = await code_agent.generate_code(code_request)
                
                assert "sort" in code_result.code
                assert code_result.language == "python"


class TestAgentMetrics:
    """Tests for agent metrics tracking."""
    
    @pytest.mark.asyncio
    async def test_metrics_update_on_success(self, mock_pydantic_agent, mock_logfire):
        """Test that metrics are updated on successful requests."""
        mock_response_data = ChatResponse(message="Success", confidence=0.9)
        mock_pydantic_agent.run.return_value.data = mock_response_data
        
        with patch('src.agents.chat_agent.Agent', return_value=mock_pydantic_agent):
            agent = ChatAgent()
            initial_metrics = agent.get_metrics()
            
            assert initial_metrics.total_requests == 0
            
            await agent.chat("Test", ConversationHistory(messages=[], session_id="metrics-test"))
            
            updated_metrics = agent.get_metrics()
            assert updated_metrics.total_requests == 1
            assert updated_metrics.successful_requests == 1
            assert updated_metrics.success_rate == 100.0
    
    @pytest.mark.asyncio
    async def test_metrics_update_on_failure(self, mock_pydantic_agent, mock_logfire):
        """Test that metrics are updated on failed requests."""
        mock_pydantic_agent.run.side_effect = Exception("API Error")
        
        with patch('src.agents.chat_agent.Agent', return_value=mock_pydantic_agent):
            agent = ChatAgent()
            
            with pytest.raises(Exception):
                await agent.chat("Test", ConversationHistory(messages=[], session_id="failure-test"))
            
            metrics = agent.get_metrics()
            assert metrics.total_requests == 1
            assert metrics.failed_requests == 1
            assert metrics.success_rate == 0.0