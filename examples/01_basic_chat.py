#!/usr/bin/env python3
"""
Basic Chat Example

This example demonstrates how to use the ChatAgent for simple conversations.
It shows:
- Creating a chat agent
- Sending messages
- Handling responses
- Using conversation history
"""

import asyncio
from src.agents import ChatAgent
from src.models import ConversationHistory, Settings


async def main():
    # Initialize settings (will load from .env)
    settings = Settings()
    
    # Create a chat agent
    print("Creating Chat Agent...")
    agent = ChatAgent()
    
    # Create conversation history to maintain context
    conversation = ConversationHistory(messages=[], session_id="example-chat")
    
    # Example conversation
    messages = [
        "Hello! Can you help me understand how to use Python decorators?",
        "Can you show me a simple example?",
        "What about decorators with arguments?",
        "Thanks! That's very helpful."
    ]
    
    print("\n" + "="*50)
    print("Starting Conversation")
    print("="*50 + "\n")
    
    for message in messages:
        # Display user message
        print(f"👤 User: {message}")
        
        # Get response from agent
        response = await agent.chat(
            message=message,
            conversation_history=conversation
        )
        
        # Display assistant response
        print(f"🤖 Assistant: {response.message}")
        
        # Show confidence score
        print(f"   [Confidence: {response.confidence:.2f}]")
        
        # Show suggested actions if any
        if response.suggested_actions:
            print("   Suggested actions:")
            for action in response.suggested_actions:
                print(f"   - {action}")
        
        print()  # Empty line for readability
    
    # Show conversation summary
    print("\n" + "="*50)
    print(f"Conversation Summary")
    print("="*50)
    print(f"Total messages: {len(conversation.messages)}")
    print(f"Session ID: {conversation.session_id}")
    
    # You can save the conversation for later
    # conversation.save_to_file("chat_history.json")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())