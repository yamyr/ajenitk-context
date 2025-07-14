#!/usr/bin/env python3
"""
Advanced Features Example

This example demonstrates advanced usage patterns:
- Custom agent configuration
- Multiple model providers
- Conversation memory management
- Tool integration
- Error handling and retries
- Async patterns
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any

from src.agents import ChatAgent, CodeAgent, AnalysisAgent
from src.models import (
    AgentConfig,
    ConversationHistory,
    Message,
    MessageRole,
    CodeGenerationRequest,
    Settings
)
from src.monitoring import monitor_operation
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class AdvancedChatAgent(ChatAgent):
    """Extended chat agent with custom functionality."""
    
    def __init__(self, config: AgentConfig = None):
        # Custom configuration
        if config is None:
            config = AgentConfig(
                name="AdvancedChatAgent",
                model="openai:gpt-4",  # Can switch to other providers
                temperature=0.7,
                max_tokens=2000,
                max_retries=3,
                timeout=30.0,
                system_message="You are an advanced AI assistant with expertise in software development."
            )
        super().__init__(config)
    
    async def chat_with_context(
        self,
        message: str,
        context_files: List[Path],
        conversation_history: ConversationHistory
    ) -> str:
        """Chat with file context."""
        
        # Build context from files
        context_parts = ["Context from files:"]
        for file_path in context_files:
            if file_path.exists():
                content = file_path.read_text()
                context_parts.append(f"\n--- File: {file_path.name} ---\n{content}")
        
        # Combine context with message
        full_message = "\n".join(context_parts) + f"\n\nUser question: {message}"
        
        # Get response
        response = await self.chat(full_message, conversation_history)
        return response.message


async def conversation_memory_example():
    """Demonstrate conversation memory management."""
    
    console.print("\n[bold]Conversation Memory Example[/bold]\n")
    
    # Create agent with specific configuration
    config = AgentConfig(
        name="MemoryAgent",
        model="openai:gpt-4",
        temperature=0.5,
        system_message="You are a helpful assistant. Remember our conversation context."
    )
    
    agent = ChatAgent(config)
    
    # Create conversation history
    conversation = ConversationHistory(
        messages=[],
        session_id="memory-demo",
        metadata={"user": "demo_user", "topic": "python_programming"}
    )
    
    # Simulate a conversation
    messages = [
        "My name is Alice and I'm learning Python.",
        "What are the main data structures I should learn?",
        "Can you explain lists in more detail?",
        "What's my name again?",  # Test memory
        "What topic are we discussing?"  # Test context retention
    ]
    
    for message in messages:
        console.print(f"\n[cyan]User:[/cyan] {message}")
        
        # Get response with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Thinking...", total=None)
            
            response = await agent.chat(message, conversation)
            
        console.print(f"[green]Assistant:[/green] {response.message}")
    
    # Save conversation
    console.print("\n[bold]Saving conversation...[/bold]")
    
    conversation_file = Path("conversation_history.json")
    conversation_data = {
        "session_id": conversation.session_id,
        "metadata": conversation.metadata,
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else None
            }
            for msg in conversation.messages
        ]
    }
    
    conversation_file.write_text(json.dumps(conversation_data, indent=2))
    console.print(f"✅ Saved to {conversation_file}")
    
    # Load and continue conversation
    console.print("\n[bold]Loading and continuing conversation...[/bold]")
    
    loaded_data = json.loads(conversation_file.read_text())
    loaded_conversation = ConversationHistory(
        messages=[
            Message(role=MessageRole(msg["role"]), content=msg["content"])
            for msg in loaded_data["messages"]
        ],
        session_id=loaded_data["session_id"],
        metadata=loaded_data["metadata"]
    )
    
    continuation_message = "Can you summarize what we've discussed so far?"
    console.print(f"\n[cyan]User:[/cyan] {continuation_message}")
    
    response = await agent.chat(continuation_message, loaded_conversation)
    console.print(f"[green]Assistant:[/green] {response.message}")


async def multi_model_example():
    """Demonstrate using multiple model providers."""
    
    console.print("\n[bold]Multi-Model Provider Example[/bold]\n")
    
    # Define different model configurations
    models = [
        ("OpenAI GPT-4", "openai:gpt-4"),
        ("Anthropic Claude", "anthropic:claude-3-5-sonnet"),
        ("Google Gemini", "google:gemini-2.0"),
        # ("Local Ollama", "ollama:llama2"),  # If you have Ollama running
    ]
    
    prompt = "Write a haiku about programming in Python."
    
    for model_name, model_id in models:
        console.print(f"\n[bold]{model_name}:[/bold]")
        
        try:
            # Create agent with specific model
            config = AgentConfig(
                name=f"Agent_{model_name.replace(' ', '_')}",
                model=model_id,
                temperature=0.8
            )
            
            agent = ChatAgent(config)
            
            # Get response
            with monitor_operation(f"multi_model_{model_name}", agent_name=config.name):
                response = await agent.chat(
                    prompt,
                    ConversationHistory(messages=[], session_id=f"demo_{model_name}")
                )
            
            console.print(response.message)
            console.print(f"[dim]Confidence: {response.confidence:.2f}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Make sure you have configured the API key for this provider[/yellow]")


async def error_handling_example():
    """Demonstrate error handling and retry mechanisms."""
    
    console.print("\n[bold]Error Handling Example[/bold]\n")
    
    # Create agent with retry configuration
    config = AgentConfig(
        name="ErrorHandlingAgent",
        model="openai:gpt-4",
        max_retries=3,
        timeout=5.0,  # Short timeout to demonstrate retries
        temperature=0.5
    )
    
    agent = CodeAgent(config)
    
    # Test various error scenarios
    test_cases = [
        {
            "name": "Valid Request",
            "request": CodeGenerationRequest(
                description="Create a simple hello world function",
                language="python"
            ),
            "should_fail": False
        },
        {
            "name": "Complex Request (might timeout)",
            "request": CodeGenerationRequest(
                description="Create a complete web application with user authentication, database, and REST API" * 10,
                language="python",
                framework="django",
                requirements=["Include all CRUD operations"] * 20
            ),
            "should_fail": True
        },
        {
            "name": "Invalid Language",
            "request": CodeGenerationRequest(
                description="Create code",
                language="invalid_language_xyz"
            ),
            "should_fail": True
        }
    ]
    
    for test_case in test_cases:
        console.print(f"\n[bold]Test: {test_case['name']}[/bold]")
        
        try:
            with monitor_operation(f"error_test_{test_case['name']}", agent_name=config.name):
                response = await agent.generate_code(test_case['request'])
                
            console.print("[green]✅ Success![/green]")
            if hasattr(response, 'code'):
                console.print(f"Generated {len(response.code)} characters of code")
                
        except asyncio.TimeoutError:
            console.print("[yellow]⏱️ Request timed out (as expected)[/yellow]")
            
        except Exception as e:
            console.print(f"[red]❌ Error: {type(e).__name__}: {e}[/red]")
            
            if test_case['should_fail']:
                console.print("[dim]This error was expected for demonstration[/dim]")


async def parallel_processing_example():
    """Demonstrate parallel agent processing."""
    
    console.print("\n[bold]Parallel Processing Example[/bold]\n")
    console.print("Running multiple agents in parallel...\n")
    
    # Create different agents
    chat_agent = ChatAgent()
    code_agent = CodeAgent()
    analysis_agent = AnalysisAgent()
    
    # Define tasks
    async def chat_task():
        response = await chat_agent.chat(
            "Explain the benefits of async programming",
            ConversationHistory(messages=[], session_id="parallel-chat")
        )
        return ("Chat", response.message[:100] + "...")
    
    async def code_task():
        request = CodeGenerationRequest(
            description="Create an async function that fetches data from an API",
            language="python",
            requirements=["Use aiohttp", "Include error handling"]
        )
        response = await code_agent.generate_code(request)
        return ("Code", f"Generated {response.language} code ({len(response.code)} chars)")
    
    async def analysis_task():
        from src.models import CodeAnalysisRequest
        request = CodeAnalysisRequest(
            code="def add(a, b): return a + b",
            language="python",
            analysis_types=["quality"]
        )
        response = await analysis_agent.analyze_code(request)
        return ("Analysis", f"Score: {response.overall_score}/10.0")
    
    # Run tasks in parallel
    start_time = asyncio.get_event_loop().time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task1 = progress.add_task("Chat Agent", total=None)
        task2 = progress.add_task("Code Agent", total=None)
        task3 = progress.add_task("Analysis Agent", total=None)
        
        # Run all tasks concurrently
        results = await asyncio.gather(
            chat_task(),
            code_task(),
            analysis_task(),
            return_exceptions=True
        )
    
    elapsed_time = asyncio.get_event_loop().time() - start_time
    
    # Display results
    console.print(f"\n[bold]Completed in {elapsed_time:.2f} seconds[/bold]\n")
    
    for agent_name, result in results:
        if isinstance(result, Exception):
            console.print(f"[red]{agent_name}:[/red] Error - {result}")
        else:
            console.print(f"[green]{agent_name}:[/green] {result}")


async def tool_integration_example():
    """Demonstrate custom tool integration."""
    
    console.print("\n[bold]Tool Integration Example[/bold]\n")
    
    # Create a custom agent with tools
    class ToolAgent(ChatAgent):
        def __init__(self):
            super().__init__()
            self._setup_tools()
        
        def _setup_tools(self):
            """Setup custom tools for the agent."""
            
            # Calculator tool
            @self.agent.tool_plain
            async def calculate(expression: str) -> str:
                """Evaluate a mathematical expression."""
                try:
                    # Safe evaluation (in production, use a proper math parser)
                    result = eval(expression, {"__builtins__": {}}, {})
                    return f"Result: {result}"
                except Exception as e:
                    return f"Error: {e}"
            
            # File reader tool
            @self.agent.tool_plain
            async def read_file(file_path: str) -> str:
                """Read contents of a file."""
                try:
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        return path.read_text()
                    return f"File not found: {file_path}"
                except Exception as e:
                    return f"Error reading file: {e}"
            
            # Current time tool
            @self.agent.tool_plain
            async def get_current_time() -> str:
                """Get the current date and time."""
                from datetime import datetime
                return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create agent with tools
    tool_agent = ToolAgent()
    
    # Test tool usage
    test_prompts = [
        "What is 123 * 456?",
        "What's the current time?",
        "Calculate the square root of 144",
        "Read the contents of the requirements.txt file"
    ]
    
    conversation = ConversationHistory(messages=[], session_id="tool-demo")
    
    for prompt in test_prompts:
        console.print(f"\n[cyan]User:[/cyan] {prompt}")
        
        response = await tool_agent.chat(prompt, conversation)
        console.print(f"[green]Assistant:[/green] {response.message}")


async def main():
    """Run all advanced examples."""
    
    examples = [
        ("Conversation Memory Management", conversation_memory_example),
        ("Multi-Model Providers", multi_model_example),
        ("Error Handling & Retries", error_handling_example),
        ("Parallel Processing", parallel_processing_example),
        ("Tool Integration", tool_integration_example)
    ]
    
    console.print("[bold]Advanced Features Examples[/bold]")
    console.print("=" * 60)
    
    for i, (name, func) in enumerate(examples, 1):
        console.print(f"\n{i}. {name}")
    console.print(f"\n{len(examples) + 1}. Run all examples")
    console.print(f"{len(examples) + 2}. Exit")
    
    while True:
        choice = input("\nSelect an example (enter number): ")
        
        try:
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(examples):
                await examples[choice_num - 1][1]()
            elif choice_num == len(examples) + 1:
                for name, func in examples:
                    console.print(f"\n{'=' * 60}")
                    console.print(f"[bold]{name}[/bold]")
                    console.print('=' * 60)
                    await func()
            elif choice_num == len(examples) + 2:
                console.print("\n[yellow]Exiting...[/yellow]")
                break
            else:
                console.print("[red]Invalid choice[/red]")
                
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    # Load settings
    settings = Settings()
    
    # Run examples
    asyncio.run(main())