"""General chat agent implementation."""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from ..models.schemas import (
    AgentConfig,
    AgentRole,
    ConversationHistory,
    Message,
    MessageRole,
)
from ..utils.dependencies import ChatAgentDependencies
from .base_agent import BaseAgent


class ChatResponse(BaseModel):
    """Response from the chat agent."""
    message: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_actions: Optional[List[str]] = None
    context_used: Optional[Dict[str, Any]] = None


class ChatAgent(BaseAgent[ChatResponse, ChatAgentDependencies]):
    """Agent specialized in conversational interactions."""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the chat agent."""
        if config is None:
            config = AgentConfig(
                name="chat_assistant",
                role=AgentRole.CHAT_ASSISTANT,
                model="openai:gpt-4o",
                temperature=0.7,  # Balanced temperature for chat
                tools=["search_context", "remember_context", "suggest_next_steps"]
            )
        
        super().__init__(
            config=config,
            output_type=ChatResponse,
            dependencies_type=ChatAgentDependencies
        )
    
    def get_default_prompt(self) -> str:
        """Get the default system prompt for chat."""
        return """You are a helpful and knowledgeable AI assistant. Your role is to:

1. Provide accurate, helpful, and relevant responses
2. Maintain context throughout the conversation
3. Ask clarifying questions when needed
4. Suggest next steps or related topics when appropriate
5. Be concise yet comprehensive in your answers
6. Adapt your tone based on the conversation context

Always structure your response as a ChatResponse with:
- message: Your main response to the user
- confidence: Your confidence level in the response (0.0-1.0)
- suggested_actions: Optional list of suggested next steps or related queries
- context_used: Optional dictionary of context information used

Focus on being:
- Helpful and informative
- Clear and easy to understand
- Proactive in suggesting relevant information
- Respectful and professional"""
    
    def _register_tools(self) -> None:
        """Register chat-specific tools."""
        
        @self.agent.tool
        async def search_context(
            ctx: RunContext[ChatAgentDependencies],
            query: str
        ) -> Dict[str, Any]:
            """Search conversation history and context for relevant information."""
            results = {
                "found_in_history": False,
                "relevant_messages": [],
                "context_items": {}
            }
            
            # Search in conversation history
            if ctx.deps.conversation_history:
                for msg in ctx.deps.conversation_history.messages:
                    if query.lower() in msg.content.lower():
                        results["found_in_history"] = True
                        results["relevant_messages"].append({
                            "role": msg.role.value,
                            "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                            "timestamp": msg.timestamp.isoformat()
                        })
            
            # Search in context
            for key, value in ctx.deps.context.items():
                if query.lower() in str(value).lower():
                    results["context_items"][key] = str(value)[:100]
            
            return results
        
        @self.agent.tool
        async def remember_context(
            ctx: RunContext[ChatAgentDependencies],
            key: str,
            value: Any
        ) -> bool:
            """Store information in the conversation context."""
            try:
                ctx.deps.update_context(**{key: value})
                return True
            except Exception:
                return False
        
        @self.agent.tool
        async def analyze_sentiment(
            ctx: RunContext[ChatAgentDependencies],
            text: str
        ) -> Dict[str, Any]:
            """Analyze the sentiment of the user's message."""
            # Simple keyword-based sentiment analysis
            positive_words = ["good", "great", "excellent", "happy", "thanks", "appreciate"]
            negative_words = ["bad", "poor", "terrible", "unhappy", "frustrated", "angry"]
            question_words = ["what", "how", "why", "when", "where", "who", "which"]
            
            text_lower = text.lower()
            
            sentiment = "neutral"
            if any(word in text_lower for word in positive_words):
                sentiment = "positive"
            elif any(word in text_lower for word in negative_words):
                sentiment = "negative"
            
            is_question = any(word in text_lower for word in question_words) or text.strip().endswith("?")
            
            return {
                "sentiment": sentiment,
                "is_question": is_question,
                "urgency": "high" if "urgent" in text_lower or "asap" in text_lower else "normal"
            }
        
        @self.agent.tool
        async def suggest_next_steps(
            ctx: RunContext[ChatAgentDependencies],
            topic: str,
            conversation_length: int
        ) -> List[str]:
            """Suggest relevant next steps or follow-up questions."""
            suggestions = []
            
            # Based on topic keywords
            if "code" in topic.lower() or "programming" in topic.lower():
                suggestions.extend([
                    "Would you like me to analyze this code for potential issues?",
                    "Should I suggest improvements or optimizations?",
                    "Do you need help with testing this code?"
                ])
            elif "error" in topic.lower() or "bug" in topic.lower():
                suggestions.extend([
                    "Can you share the full error message or stack trace?",
                    "What steps led to this error?",
                    "Have you tried any debugging steps already?"
                ])
            elif "help" in topic.lower() or "how" in topic.lower():
                suggestions.extend([
                    "Would you like a step-by-step guide?",
                    "Should I provide code examples?",
                    "Do you need more detailed explanation?"
                ])
            
            # Based on conversation length
            if conversation_length > 10:
                suggestions.append("Would you like me to summarize our conversation so far?")
            
            return suggestions[:3]  # Limit to 3 suggestions
        
        @self.agent.tool
        async def format_response(
            ctx: RunContext[ChatAgentDependencies],
            content: str,
            response_type: str = "general"
        ) -> str:
            """Format response based on type and context."""
            if response_type == "code_explanation":
                return f"Let me explain this code:\n\n{content}"
            elif response_type == "error_help":
                return f"I understand you're encountering an error. {content}"
            elif response_type == "tutorial":
                return f"Here's a guide to help you:\n\n{content}"
            else:
                return content
    
    async def chat(
        self,
        message: str,
        conversation_history: Optional[ConversationHistory] = None,
        deps: Optional[ChatAgentDependencies] = None
    ) -> ChatResponse:
        """
        Process a chat message and generate a response.
        
        Args:
            message: User's message
            conversation_history: Optional conversation history
            deps: Optional dependencies override
        
        Returns:
            Chat response
        """
        if deps is None:
            deps = ChatAgentDependencies(
                settings=self.config.settings,
                config=self.config,
                conversation_history=conversation_history
            )
        elif conversation_history:
            deps.conversation_history = conversation_history
        
        # Run the agent
        response = await self.run(message, deps, conversation_history)
        
        # Update conversation history if provided
        if conversation_history:
            conversation_history.add_message(MessageRole.USER, message)
            conversation_history.add_message(MessageRole.ASSISTANT, response.message)
        
        return response
    
    def chat_sync(
        self,
        message: str,
        conversation_history: Optional[ConversationHistory] = None,
        deps: Optional[ChatAgentDependencies] = None
    ) -> ChatResponse:
        """Synchronous version of chat."""
        import asyncio
        return asyncio.run(self.chat(message, conversation_history, deps))
    
    async def start_conversation(
        self,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> ConversationHistory:
        """
        Start a new conversation with optional initial context.
        
        Args:
            initial_context: Optional initial context
        
        Returns:
            New conversation history object
        """
        import uuid
        
        history = ConversationHistory(
            messages=[],
            session_id=str(uuid.uuid4())
        )
        
        if initial_context:
            # Create dependencies with initial context
            deps = ChatAgentDependencies(
                settings=self.config.settings,
                config=self.config,
                context=initial_context
            )
            
            # Generate a welcome message
            welcome_prompt = "Generate a friendly welcome message for a new conversation."
            response = await self.run(welcome_prompt, deps)
            
            history.add_message(MessageRole.SYSTEM, "New conversation started")
            history.add_message(MessageRole.ASSISTANT, response.message)
        
        return history