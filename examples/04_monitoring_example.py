#!/usr/bin/env python3
"""
Monitoring and Observability Example

This example demonstrates how to use the monitoring features:
- Real-time metrics collection
- Performance tracking
- Alert management
- Dashboard visualization
- Metrics export
"""

import asyncio
import time
import random
from src.agents import ChatAgent, CodeAgent, AnalysisAgent
from src.models import CodeGenerationRequest, CodeAnalysisRequest, ConversationHistory
from src.monitoring import (
    metrics_collector,
    alert_manager,
    create_monitoring_dashboard,
    export_metrics,
    monitor_operation
)
from src.utils import setup_logfire
from rich.console import Console
from rich.live import Live

console = Console()


async def simulate_agent_activity():
    """Simulate various agent activities to generate metrics."""
    
    # Create agents
    chat_agent = ChatAgent()
    code_agent = CodeAgent()
    analysis_agent = AnalysisAgent()
    
    # Simulate chat conversations
    console.print("\n[bold]Simulating Chat Agent Activity...[/bold]")
    conversation = ConversationHistory(messages=[], session_id="sim-chat")
    
    chat_prompts = [
        "What is Python?",
        "How do I handle errors in Python?",
        "Explain async/await",
        "What are decorators?",
        "This is an invalid prompt that might fail" * 100  # Long prompt to simulate potential failure
    ]
    
    for i, prompt in enumerate(chat_prompts):
        try:
            # Add some randomness to simulate real-world conditions
            if random.random() > 0.9:  # 10% chance of simulated failure
                raise Exception("Simulated network error")
            
            with monitor_operation(f"chat_simulation_{i}", agent_name="ChatAgent"):
                response = await chat_agent.chat(prompt, conversation)
                console.print(f"✅ Chat {i+1}: Success")
                
                # Simulate varying response times
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
        except Exception as e:
            console.print(f"❌ Chat {i+1}: Failed - {str(e)}")
    
    # Simulate code generation
    console.print("\n[bold]Simulating Code Generation...[/bold]")
    
    code_requests = [
        CodeGenerationRequest(
            description="Create a hello world function",
            language="python"
        ),
        CodeGenerationRequest(
            description="Build a REST API with FastAPI",
            language="python",
            framework="fastapi"
        ),
        CodeGenerationRequest(
            description="Create a React component",
            language="typescript",
            framework="react"
        )
    ]
    
    for i, request in enumerate(code_requests):
        try:
            with monitor_operation(f"code_gen_{i}", agent_name="CodeAgent"):
                response = await code_agent.generate_code(request)
                console.print(f"✅ Code Generation {i+1}: {request.language} - Success")
                
                # Simulate token usage
                metrics_collector.record_model_usage(
                    model="gpt-4",
                    tokens=random.randint(100, 1000),
                    latency=random.uniform(0.5, 2.0),
                    cost=random.uniform(0.01, 0.10)
                )
                
        except Exception as e:
            console.print(f"❌ Code Generation {i+1}: Failed - {str(e)}")
    
    # Simulate code analysis
    console.print("\n[bold]Simulating Code Analysis...[/bold]")
    
    sample_code = """
def calculate(a, b):
    return a + b
"""
    
    analysis_request = CodeAnalysisRequest(
        code=sample_code,
        language="python",
        analysis_types=["quality", "security"]
    )
    
    try:
        with monitor_operation("code_analysis", agent_name="AnalysisAgent"):
            response = await analysis_agent.analyze_code(analysis_request)
            console.print("✅ Code Analysis: Success")
    except Exception as e:
        console.print(f"❌ Code Analysis: Failed - {str(e)}")
    
    # Simulate tool usage
    console.print("\n[bold]Simulating Tool Usage...[/bold]")
    
    tools = ["file_reader", "web_search", "calculator", "database_query"]
    
    for tool in tools:
        success = random.random() > 0.2  # 80% success rate
        execution_time = random.uniform(0.1, 1.0)
        
        metrics_collector.record_tool_usage(
            tool_name=tool,
            agent_name=random.choice(["ChatAgent", "CodeAgent"]),
            success=success,
            execution_time=execution_time,
            error=None if success else "Simulated tool error"
        )
        
        status = "✅" if success else "❌"
        console.print(f"{status} Tool '{tool}': {'Success' if success else 'Failed'}")


async def monitoring_demo():
    """Demonstrate monitoring capabilities."""
    
    # Setup Logfire
    console.print("[bold]Setting up monitoring...[/bold]")
    setup_logfire()
    
    # Start generating metrics
    console.print("\n[bold]Starting activity simulation...[/bold]")
    await simulate_agent_activity()
    
    # Show static dashboard
    console.print("\n" + "="*60)
    console.print("[bold]Current System Metrics[/bold]")
    console.print("="*60 + "\n")
    
    dashboard = create_monitoring_dashboard()
    console.print(dashboard)
    
    # Check for alerts
    console.print("\n[bold]Checking for alerts...[/bold]")
    alerts = alert_manager.check_alerts()
    
    if alerts:
        console.print(f"\n🚨 [red]Found {len(alerts)} alerts:[/red]")
        for alert in alerts:
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(alert["severity"], "⚪")
            console.print(f"{emoji} [{alert['severity']}] {alert['message']}")
    else:
        console.print("✅ [green]No alerts detected[/green]")
    
    # Export metrics
    console.print("\n[bold]Exporting metrics...[/bold]")
    
    # Export as JSON
    json_export = export_metrics("json")
    with open("metrics_export.json", "w") as f:
        f.write(json_export)
    console.print("✅ Exported metrics to metrics_export.json")
    
    # Export as Markdown
    md_export = export_metrics("markdown")
    with open("metrics_report.md", "w") as f:
        f.write(md_export)
    console.print("✅ Exported report to metrics_report.md")
    
    # Show system health
    health = metrics_collector.get_system_health()
    console.print("\n[bold]System Health Summary:[/bold]")
    console.print(f"  Status: {health['status']}")
    console.print(f"  Uptime: {health['uptime_seconds']:.0f}s")
    console.print(f"  Success Rate: {health['success_rate']:.1f}%")
    console.print(f"  Total Requests: {health['total_requests']}")
    console.print(f"  Total Cost: ${health['total_cost']:.2f}")
    console.print(f"  Total Tokens: {health['total_tokens']:,}")


async def live_dashboard_demo():
    """Demonstrate live dashboard functionality."""
    
    console.print("[bold]Live Dashboard Demo[/bold]")
    console.print("This will show a live updating dashboard for 30 seconds.")
    console.print("Press Ctrl+C to stop early.\n")
    
    # Start background activity
    activity_task = asyncio.create_task(continuous_activity_simulation())
    
    # Show live dashboard for 30 seconds
    try:
        with Live(create_monitoring_dashboard(), refresh_per_second=1, console=console) as live:
            for i in range(30):
                await asyncio.sleep(1)
                live.update(create_monitoring_dashboard())
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")
    
    # Cancel background activity
    activity_task.cancel()
    try:
        await activity_task
    except asyncio.CancelledError:
        pass


async def continuous_activity_simulation():
    """Continuously generate activity for live dashboard."""
    
    agents = ["ChatAgent", "CodeAgent", "AnalysisAgent"]
    tools = ["file_reader", "web_search", "calculator", "database_query"]
    models = ["gpt-4", "claude-3", "gemini-pro"]
    
    while True:
        # Simulate agent request
        agent = random.choice(agents)
        success = random.random() > 0.1  # 90% success rate
        response_time = random.uniform(0.1, 2.0)
        
        metrics_collector.record_agent_request(
            agent_name=agent,
            success=success,
            response_time=response_time,
            tokens=random.randint(50, 500),
            cost=random.uniform(0.01, 0.05)
        )
        
        # Simulate tool usage
        if random.random() > 0.5:
            tool = random.choice(tools)
            tool_success = random.random() > 0.2
            
            metrics_collector.record_tool_usage(
                tool_name=tool,
                agent_name=agent,
                success=tool_success,
                execution_time=random.uniform(0.05, 0.5)
            )
        
        # Simulate model usage
        if random.random() > 0.3:
            model = random.choice(models)
            metrics_collector.record_model_usage(
                model=model,
                tokens=random.randint(100, 1000),
                latency=random.uniform(0.5, 1.5),
                cost=random.uniform(0.02, 0.10)
            )
        
        # Occasionally generate an error
        if random.random() > 0.95:
            metrics_collector.record_error(
                component=agent,
                error_type="SimulatedError",
                error_message="This is a simulated error for demo purposes",
                context={"demo": True}
            )
        
        await asyncio.sleep(random.uniform(0.1, 0.5))


async def main():
    """Main function to run monitoring examples."""
    
    while True:
        console.print("\n" + "="*60)
        console.print("[bold]Monitoring and Observability Examples[/bold]")
        console.print("="*60)
        console.print("\n1. Run monitoring demo (static)")
        console.print("2. Live dashboard demo (30 seconds)")
        console.print("3. Exit")
        
        choice = input("\nSelect an option (1-3): ")
        
        if choice == "1":
            await monitoring_demo()
        elif choice == "2":
            await live_dashboard_demo()
        elif choice == "3":
            console.print("\n[yellow]Exiting...[/yellow]")
            break
        else:
            console.print("[red]Invalid choice. Please try again.[/red]")


if __name__ == "__main__":
    asyncio.run(main())