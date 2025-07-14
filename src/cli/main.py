"""Main CLI entry point for the ajentik system."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.columns import Columns
from rich import box
import questionary
from questionary import Style

from ..agents import AnalysisAgent, ChatAgent, CodeAgent
from ..models import (
    CodeAnalysisRequest,
    CodeGenerationRequest,
    ConversationHistory,
    Settings,
)
from ..utils import setup_logfire
from .tools_command import add_tools_command
from .mcp_command import add_mcp_command

# Initialize Rich console
console = Console()

# Define custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--no-logfire", is_flag=True, help="Disable Logfire monitoring")
@click.pass_context
def cli(ctx: click.Context, debug: bool, no_logfire: bool) -> None:
    """Ajentik AI CLI with PydanticAI and Logfire integration."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    
    # Load settings
    settings = Settings()
    ctx.obj["settings"] = settings
    
    # Setup Logfire unless disabled
    if not no_logfire:
        try:
            setup_logfire(settings.get_logfire_config())
            console.print("[green]✓[/green] Logfire monitoring enabled")
        except Exception as e:
            if debug:
                console.print(f"[yellow]Warning:[/yellow] Failed to setup Logfire: {e}")
    
    # Display welcome message
    if not ctx.invoked_subcommand:
        welcome_panel = Panel.fit(
            "[bold blue]Ajentik AI System[/bold blue]\n"
            "Powered by PydanticAI with Logfire monitoring\n\n"
            "[dim]Use --help to see available commands[/dim]",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(welcome_panel)
        
        # Show interactive menu
        show_menu()


@cli.command()
@click.option("--history", is_flag=True, help="Load conversation history")
@click.option("--personality", default="helpful", help="Chat personality")
@click.option("--enhanced", is_flag=True, help="Use enhanced chat interface")
@click.pass_context
def chat(ctx: click.Context, history: bool, personality: str, enhanced: bool) -> None:
    """Interactive chat with AI agent."""
    settings = ctx.obj["settings"]
    
    if enhanced:
        # Use enhanced chat interface
        from .chat_interface import InteractiveChatSession
        session = InteractiveChatSession()
        session.run()
    else:
        # Use basic chat interface
        console.print("[bold]Starting chat session...[/bold]")
        console.print("Type 'exit' or 'quit' to end the conversation.\n")
        
        # Create chat agent
        agent = ChatAgent()
        
        # Create or load conversation history
        conversation_history = ConversationHistory(messages=[], session_id="cli-session")
        
        # Start chat loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
                
                if user_input.lower() in ["exit", "quit"]:
                    console.print("\n[yellow]Ending chat session. Goodbye![/yellow]")
                    break
                
                # Show thinking indicator with progress
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=True
                ) as progress:
                    task = progress.add_task("[yellow]AI is thinking...[/yellow]", total=None)
                    # Run agent
                    response = agent.chat_sync(
                        message=user_input,
                        conversation_history=conversation_history
                    )
                    progress.stop()
                
                # Display response with markdown formatting
                response_panel = Panel(
                    Markdown(response.message),
                    title="[bold green]Assistant[/bold green]",
                    border_style="green",
                    padding=(1, 2)
                )
                console.print(response_panel)
                
                # Show confidence if in debug mode
                if ctx.obj["debug"]:
                    console.print(f"[dim]Confidence: {response.confidence:.2f}[/dim]")
                
                # Show suggested actions if any
                if response.suggested_actions:
                    console.print("\n[dim]Suggested actions:[/dim]")
                    for action in response.suggested_actions:
                        console.print(f"  • {action}")
                
                console.print()  # Empty line for readability
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Chat interrupted. Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                if ctx.obj["debug"]:
                    import traceback
                    traceback.print_exc()


@cli.group()
def code() -> None:
    """Code generation and analysis commands."""
    pass


@code.command("generate")
@click.option("--language", "-l", default="python", help="Programming language")
@click.option("--framework", "-f", help="Framework to use")
@click.option("--output", "-o", help="Output file path")
@click.pass_context
def generate_code(
    ctx: click.Context,
    language: str,
    framework: Optional[str],
    output: Optional[str]
) -> None:
    """Generate code using AI."""
    console.print("[bold]Code Generation Assistant[/bold]\n")
    
    # Get description with enhanced prompt
    description = questionary.text(
        "What code would you like me to generate?",
        multiline=True,
        style=custom_style,
        instruction="(Press Ctrl+D or Ctrl+Z when done)"
    ).ask()
    
    if not description:
        console.print("[yellow]Code generation cancelled.[/yellow]")
        return
    
    # Get requirements interactively
    requirements = []
    add_requirements = questionary.confirm(
        "Would you like to add specific requirements?",
        default=True,
        style=custom_style
    ).ask()
    
    if add_requirements:
        console.print("\n[dim]Add requirements (select 'Done' when finished):[/dim]")
        while True:
            req_choices = requirements + ["✅ Done", "❌ Cancel"]
            action = questionary.select(
                "Requirements:",
                choices=req_choices if requirements else ["➕ Add requirement", "✅ Done", "❌ Cancel"],
                style=custom_style
            ).ask()
            
            if action == "✅ Done":
                break
            elif action == "❌ Cancel":
                console.print("[yellow]Code generation cancelled.[/yellow]")
                return
            elif action == "➕ Add requirement" or action not in ["✅ Done", "❌ Cancel"]:
                new_req = questionary.text(
                    "Enter requirement:",
                    style=custom_style
                ).ask()
                if new_req:
                    requirements.append(new_req)
    
    # Create request
    request = CodeGenerationRequest(
        description=description,
        language=language,
        framework=framework,
        requirements=requirements if requirements else None
    )
    
    # Generate code
    console.print("\n[bold yellow]Generating code...[/bold yellow]")
    
    agent = CodeAgent()
    
    try:
        with console.status("Working..."):
            response = agent.generate_code_sync(request)
        
        # Display generated code with syntax highlighting
        console.print(f"\n[bold green]Generated {response.language} code:[/bold green]")
        syntax = Syntax(
            response.code,
            response.language,
            theme="monokai",
            line_numbers=True
        )
        code_panel = Panel(
            syntax,
            title=f"{response.language.title()} Code",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(code_panel)
        
        if response.explanation:
            console.print(f"\n[bold]Explanation:[/bold] {response.explanation}")
        
        if response.dependencies:
            console.print("\n[bold]Dependencies:[/bold]")
            for dep in response.dependencies:
                console.print(f"  • {dep}")
        
        if response.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in response.warnings:
                console.print(f"  ⚠ {warning}")
        
        # Save to file if requested
        if output:
            save = Confirm.ask(f"\nSave to {output}?", default=True)
            if save:
                Path(output).write_text(response.code)
                console.print(f"[green]✓[/green] Saved to {output}")
        else:
            # Ask if user wants to save
            save_file = questionary.confirm(
                "Would you like to save this code to a file?",
                default=True,
                style=custom_style
            ).ask()
            
            if save_file:
                filename = questionary.text(
                    "Enter filename:",
                    default=f"generated.{response.language}",
                    style=custom_style
                ).ask()
                
                if filename:
                    Path(filename).write_text(response.code)
                    console.print(f"[green]✓[/green] Saved to {filename}")
        
    except Exception as e:
        console.print(f"[red]Error generating code: {e}[/red]")
        if ctx.obj["debug"]:
            import traceback
            traceback.print_exc()


@code.command("analyze")
@click.argument("file", type=click.Path(exists=True), required=False)
@click.option("--types", "-t", multiple=True, default=["quality", "security", "performance"])
@click.pass_context
def analyze_code(ctx: click.Context, file: Optional[str], types: tuple) -> None:
    """Analyze code file for issues."""
    # If no file provided, show file browser
    if not file:
        file = questionary.path(
            "Select a file to analyze:",
            only_files=True,
            style=custom_style
        ).ask()
        
        if not file:
            console.print("[yellow]No file selected.[/yellow]")
            return
    
    console.print(f"[bold]Analyzing {file}...[/bold]\n")
    
    # Read file
    try:
        code_content = Path(file).read_text()
        language = Path(file).suffix[1:] if Path(file).suffix else "unknown"
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return
    
    # Create request
    request = CodeAnalysisRequest(
        code=code_content,
        language=language,
        analysis_types=list(types),
        include_suggestions=True
    )
    
    # Analyze code
    agent = AnalysisAgent()
    
    try:
        # Show analysis progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("[cyan]Analyzing code structure...[/cyan]", total=None)
            progress.update(task, description="[cyan]Checking for quality issues...[/cyan]")
            progress.update(task, description="[cyan]Scanning for security vulnerabilities...[/cyan]")
            progress.update(task, description="[cyan]Evaluating performance...[/cyan]")
            
            response = agent.analyze_code_sync(request)
            progress.stop()
        
        # Display summary
        console.print(Panel(response.summary, title="Analysis Summary", border_style="blue"))
        
        # Display issues
        if response.issues:
            table = Table(title="Issues Found")
            table.add_column("Type", style="cyan")
            table.add_column("Severity", style="yellow")
            table.add_column("Line", style="green")
            table.add_column("Description")
            
            for issue in response.issues:
                severity_color = {
                    "high": "red",
                    "medium": "yellow",
                    "low": "green"
                }.get(issue.severity, "white")
                
                table.add_row(
                    issue.type,
                    f"[{severity_color}]{issue.severity}[/{severity_color}]",
                    str(issue.line_number) if issue.line_number else "-",
                    issue.description
                )
            
            console.print(table)
        else:
            console.print("[green]No issues found![/green]")
        
        # Display metrics
        if response.metrics:
            console.print("\n[bold]Code Metrics:[/bold]")
            for metric, value in response.metrics.items():
                console.print(f"  • {metric}: {value}")
        
        # Display suggestions
        if response.suggestions:
            console.print("\n[bold]Suggestions:[/bold]")
            for suggestion in response.suggestions:
                console.print(f"  → {suggestion}")
        
        # Overall score
        console.print(f"\n[bold]Overall Score:[/bold] {response.overall_score:.1f}/10.0")
        
    except Exception as e:
        console.print(f"[red]Error analyzing code: {e}[/red]")
        if ctx.obj["debug"]:
            import traceback
            traceback.print_exc()


@cli.command()
@click.option("--live", is_flag=True, help="Show live monitoring dashboard")
@click.option("--export", type=click.Choice(["json", "markdown"]), help="Export metrics")
@click.option("--alerts", is_flag=True, help="Show active alerts")
@click.pass_context
def monitor(ctx: click.Context, live: bool, export: Optional[str], alerts: bool) -> None:
    """Open monitoring dashboard with enhanced features."""
    from ..monitoring import (
        create_monitoring_dashboard,
        live_monitoring_dashboard,
        export_metrics as export_metrics_fn,
        alert_manager
    )
    
    if live:
        # Show live monitoring dashboard
        console.print("[bold]Starting live monitoring dashboard...[/bold]")
        console.print("[dim]Press Ctrl+C to exit[/dim]\n")
        
        try:
            import asyncio
            asyncio.run(live_monitoring_dashboard(refresh_rate=2.0))
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped.[/yellow]")
    
    elif export:
        # Export metrics
        console.print(f"[bold]Exporting metrics as {export}...[/bold]")
        
        try:
            output = export_metrics_fn(format=export)
            filename = f"metrics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export}"
            
            with open(filename, "w") as f:
                f.write(output)
            
            console.print(f"[green]✓ Metrics exported to {filename}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to export metrics: {e}[/red]")
    
    elif alerts:
        # Show active alerts
        console.print("[bold]Checking for active alerts...[/bold]\n")
        
        active_alerts = alert_manager.check_alerts()
        
        if not active_alerts:
            console.print("[green]✓ No active alerts[/green]")
        else:
            alert_table = Table(title="Active Alerts", box=box.ROUNDED)
            alert_table.add_column("Severity", style="bold")
            alert_table.add_column("Type")
            alert_table.add_column("Message")
            alert_table.add_column("Time")
            
            for alert in active_alerts:
                severity_color = {
                    "high": "red",
                    "medium": "yellow",
                    "low": "cyan"
                }.get(alert["severity"], "white")
                
                alert_table.add_row(
                    f"[{severity_color}]{alert['severity'].upper()}[/{severity_color}]",
                    alert["type"],
                    alert["message"],
                    alert["timestamp"]
                )
            
            console.print(alert_table)
    
    else:
        # Show static dashboard
        dashboard = create_monitoring_dashboard()
        console.print(dashboard)
        
        # Create a dashboard-like display for Logfire info
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(
            Panel(
                "[bold]Logfire Integration Info[/bold]",
                style="bold blue"
            )
        )
        
        # Body with metrics tree
        tree = Tree("📊 Available Metrics")
        
        performance = tree.add("⚡ Agent Performance")
        performance.add("Request times")
        performance.add("Success rates")
        performance.add("Response latency")
        
        tools = tree.add("🔧 Tool Usage")
        tools.add("Most used tools")
        tools.add("Tool execution times")
        tools.add("Tool failure rates")
        
        errors = tree.add("❌ Error Tracking")
        errors.add("Error frequency")
        errors.add("Error types")
        errors.add("Stack traces")
        
        tokens = tree.add("💰 Token Usage")
        tokens.add("Total consumption")
        tokens.add("Cost breakdown")
        tokens.add("Model usage stats")
        
        layout["body"].update(Panel(tree, border_style="green"))
        
        # Footer
        layout["footer"].update(
            Panel(
                "[dim]Visit https://logfire.pydantic.dev to view your traces[/dim]",
                style="dim"
            )
        )
        
        console.print("\n")
        console.print(layout)
        
        # Show monitoring options
        options = [
            "📺 View live dashboard",
            "📊 Export metrics",
            "🚨 Check alerts",
            "🌐 Open Logfire web dashboard",
            "❌ Exit"
        ]
        
        choice = questionary.select(
            "\nWhat would you like to do?",
            choices=options,
            style=custom_style
        ).ask()
        
        if choice and "live dashboard" in choice:
            ctx.invoke(monitor, live=True)
        elif choice and "Export metrics" in choice:
            format_choice = questionary.select(
                "Select export format:",
                choices=["json", "markdown"],
                style=custom_style
            ).ask()
            if format_choice:
                ctx.invoke(monitor, export=format_choice)
        elif choice and "Check alerts" in choice:
            ctx.invoke(monitor, alerts=True)
        elif choice and "Open Logfire" in choice:
            import webbrowser
            webbrowser.open("https://logfire.pydantic.dev")


@cli.command()
def config() -> None:
    """Configure the ajentik system."""
    console.print("[bold]Configuration Assistant[/bold]\n")
    
    # Check for existing .env file
    env_path = Path(".env")
    if not env_path.exists():
        create = Confirm.ask("No .env file found. Create one?", default=True)
        if create:
            # Copy from example
            example_path = Path(".env.example")
            if example_path.exists():
                env_path.write_text(example_path.read_text())
                console.print("[green]✓[/green] Created .env from .env.example")
            else:
                console.print("[yellow]No .env.example found. Creating blank .env[/yellow]")
                env_path.touch()
    
    console.print("\nEdit your .env file to configure:")
    console.print("  • API keys (OpenAI, Anthropic, etc.)")
    console.print("  • Logfire settings")
    console.print("  • Model preferences")
    console.print("  • Other options")
    
    edit = Confirm.ask("\nOpen .env in editor?", default=True)
    if edit:
        import subprocess
        import os
        
        editor = os.environ.get("EDITOR", "nano")
        try:
            subprocess.run([editor, ".env"])
        except Exception:
            console.print(f"[yellow]Could not open editor. Please edit .env manually.[/yellow]")


@cli.command()
def version() -> None:
    """Show version information."""
    try:
        from .. import __version__
        version_str = __version__
    except ImportError:
        version_str = "0.1.0"
    
    console.print("[bold]Ajentik AI System[/bold]")
    console.print(f"Version: {version_str}")
    console.print("PydanticAI: Latest")
    console.print("Python:", sys.version.split()[0])


def show_menu() -> None:
    """Show interactive main menu."""
    choices = [
        "💬 Chat - Interactive conversation with AI",
        "🔧 Generate Code - Create new code with AI assistance",
        "🔍 Analyze Code - Review code for issues and improvements",
        "🔨 Tools - Manage and execute tools",
        "📊 Monitor - View Logfire dashboard",
        "⚙️  Configure - Setup system settings",
        "❌ Exit"
    ]
    
    choice = questionary.select(
        "What would you like to do?",
        choices=choices,
        style=custom_style
    ).ask()
    
    if choice:
        if "Chat" in choice:
            ctx = click.Context(cli)
            ctx.obj = {"debug": False, "settings": Settings()}
            chat.invoke(ctx)
        elif "Generate Code" in choice:
            ctx = click.Context(cli)
            ctx.obj = {"debug": False, "settings": Settings()}
            generate_code.invoke(ctx)
        elif "Analyze Code" in choice:
            file_path = questionary.path(
                "Select file to analyze:",
                only_files=True,
                style=custom_style
            ).ask()
            if file_path:
                ctx = click.Context(cli)
                ctx.obj = {"debug": False, "settings": Settings()}
                analyze_code.invoke(ctx, file=file_path, types=("quality", "security", "performance"))
        elif "Tools" in choice:
            # Show tools submenu
            tool_choices = [
                "📋 List Tools - View available tools",
                "▶️  Run Tool - Execute a tool",
                "📚 Tool Documentation - Generate docs",
                "🔍 Validate Tool - Check tool safety",
                "⬅️  Back to main menu"
            ]
            
            tool_choice = questionary.select(
                "Tool Management:",
                choices=tool_choices,
                style=custom_style
            ).ask()
            
            if tool_choice and "List Tools" in tool_choice:
                import subprocess
                subprocess.run([sys.executable, "-m", "src.cli.main", "tools", "list", "--detailed"])
            elif tool_choice and "Run Tool" in tool_choice:
                import subprocess
                subprocess.run([sys.executable, "-m", "src.cli.main", "tools", "list"])
                tool_name = questionary.text(
                    "Enter tool name to run:",
                    style=custom_style
                ).ask()
                if tool_name:
                    subprocess.run([sys.executable, "-m", "src.cli.main", "tools", "run", tool_name])
            elif tool_choice and "Tool Documentation" in tool_choice:
                import subprocess
                subprocess.run([sys.executable, "-m", "src.cli.main", "tools", "docs"])
            elif tool_choice and "Validate Tool" in tool_choice:
                import subprocess
                subprocess.run([sys.executable, "-m", "src.cli.main", "tools", "list"])
                tool_name = questionary.text(
                    "Enter tool name to validate:",
                    style=custom_style
                ).ask()
                if tool_name:
                    subprocess.run([sys.executable, "-m", "src.cli.main", "tools", "validate", tool_name])
            elif tool_choice and "Back" in tool_choice:
                show_menu()
                return
                
        elif "Monitor" in choice:
            ctx = click.Context(cli)
            ctx.obj = {"debug": False, "settings": Settings()}
            monitor.invoke(ctx)
        elif "Configure" in choice:
            config.invoke(click.Context(cli))
        elif "Exit" in choice:
            console.print("[yellow]Goodbye! 👋[/yellow]")
            return


def main() -> None:
    """Main entry point."""
    # Add the tools command to CLI
    add_tools_command(cli)
    # Add the MCP command to CLI
    add_mcp_command(cli)
    cli()


if __name__ == "__main__":
    main()