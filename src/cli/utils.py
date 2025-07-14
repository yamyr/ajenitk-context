"""CLI utility functions for enhanced interactivity."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
from rich import box
import questionary


console = Console()


def create_file_tree(directory: Path, tree: Tree = None, ignore_patterns: List[str] = None) -> Tree:
    """Create a rich tree view of directory structure."""
    if ignore_patterns is None:
        ignore_patterns = ['.git', '__pycache__', '.pytest_cache', '.env', 'venv']
    
    if tree is None:
        tree = Tree(
            f"📁 {directory.name}",
            guide_style="bright_blue"
        )
    
    try:
        paths = sorted(
            directory.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower())
        )
        
        for path in paths:
            if any(pattern in str(path) for pattern in ignore_patterns):
                continue
                
            if path.is_dir():
                branch = tree.add(f"📁 {path.name}", style="blue")
                create_file_tree(path, branch, ignore_patterns)
            else:
                icon = get_file_icon(path.suffix)
                size = path.stat().st_size
                size_str = format_file_size(size)
                tree.add(f"{icon} {path.name} [dim]({size_str})[/dim]")
                
    except PermissionError:
        tree.add("[red]Permission denied[/red]")
    
    return tree


def get_file_icon(extension: str) -> str:
    """Get icon for file based on extension."""
    icons = {
        '.py': '🐍',
        '.js': '📜',
        '.ts': '📘',
        '.json': '📋',
        '.md': '📝',
        '.txt': '📄',
        '.yml': '⚙️',
        '.yaml': '⚙️',
        '.toml': '⚙️',
        '.sh': '🖥️',
        '.env': '🔐',
        '.git': '🔄',
        '.log': '📊',
        '.db': '💾',
        '.sql': '🗄️',
        '.html': '🌐',
        '.css': '🎨',
        '.png': '🖼️',
        '.jpg': '🖼️',
        '.jpeg': '🖼️',
        '.gif': '🖼️',
        '.svg': '🖼️',
        '.pdf': '📕',
        '.zip': '📦',
        '.tar': '📦',
        '.gz': '📦',
    }
    return icons.get(extension.lower(), '📄')


def format_file_size(size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"


def create_progress_bar(description: str = "Processing") -> Progress:
    """Create a customized progress bar."""
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        TimeRemainingColumn(),
        console=console,
        expand=True
    )


def display_code_diff(old_code: str, new_code: str, language: str = "python") -> None:
    """Display a diff between old and new code."""
    from difflib import unified_diff
    
    diff_lines = list(unified_diff(
        old_code.splitlines(keepends=True),
        new_code.splitlines(keepends=True),
        fromfile="original",
        tofile="modified",
        lineterm=""
    ))
    
    if diff_lines:
        diff_text = "".join(diff_lines)
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="Code Diff", border_style="yellow"))
    else:
        console.print("[green]No changes detected[/green]")


def create_status_dashboard() -> Layout:
    """Create a status dashboard layout."""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    # Header
    layout["header"].update(
        Panel(
            "[bold]Ajentik AI System Status[/bold]",
            style="bold blue"
        )
    )
    
    # Footer with timestamp
    layout["footer"].update(
        Panel(
            f"[dim]Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
            style="dim"
        )
    )
    
    return layout


def create_metrics_table(metrics: Dict[str, Any]) -> Table:
    """Create a table for displaying metrics."""
    table = Table(
        title="System Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    table.add_column("Status", justify="center")
    
    for metric, value in metrics.items():
        status = "✅" if value > 0 else "⚠️"
        table.add_row(metric, str(value), status)
    
    return table


def select_model_provider() -> Optional[str]:
    """Interactive model provider selection."""
    providers = {
        "OpenAI (GPT-4)": "openai",
        "Anthropic (Claude)": "anthropic",
        "Google (Gemini)": "google",
        "Groq": "groq",
        "Mistral": "mistral",
        "Local (Ollama)": "ollama"
    }
    
    choice = questionary.select(
        "Select AI model provider:",
        choices=list(providers.keys()),
        style=questionary.Style([
            ('qmark', 'fg:#673ab7 bold'),
            ('question', 'bold'),
            ('answer', 'fg:#f44336 bold'),
            ('pointer', 'fg:#673ab7 bold'),
            ('highlighted', 'fg:#673ab7 bold'),
            ('selected', 'fg:#cc5454'),
        ])
    ).ask()
    
    return providers.get(choice) if choice else None


def confirm_action(message: str, default: bool = False) -> bool:
    """Enhanced confirmation prompt."""
    return questionary.confirm(
        message,
        default=default,
        style=questionary.Style([
            ('qmark', 'fg:#ff9d00 bold'),
            ('question', 'bold'),
            ('answer', 'fg:#ff9d00 bold'),
        ])
    ).ask()


def create_spinner_context(message: str = "Processing..."):
    """Create a context manager for spinner animations."""
    from rich.spinner import Spinner
    from contextlib import contextmanager
    
    @contextmanager
    def spinner_context():
        with console.status(message, spinner="dots"):
            yield
    
    return spinner_context()


def format_agent_response(response: Any, agent_type: str = "chat") -> Panel:
    """Format agent response with appropriate styling."""
    style_map = {
        "chat": ("green", "💬"),
        "code": ("blue", "🔧"),
        "analysis": ("yellow", "🔍"),
        "error": ("red", "❌")
    }
    
    color, icon = style_map.get(agent_type, ("white", "📝"))
    
    return Panel(
        str(response),
        title=f"{icon} {agent_type.title()} Response",
        border_style=color,
        padding=(1, 2),
        expand=False
    )


def display_conversation_history(history: List[Dict[str, str]]) -> None:
    """Display conversation history in a formatted way."""
    for idx, message in enumerate(history):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        timestamp = message.get("timestamp", "")
        
        if role == "user":
            console.print(f"\n[bold cyan]You[/bold cyan] [dim]{timestamp}[/dim]")
            console.print(content)
        elif role == "assistant":
            console.print(f"\n[bold green]Assistant[/bold green] [dim]{timestamp}[/dim]")
            console.print(Panel(content, border_style="green", box=box.MINIMAL))


def create_live_output_display():
    """Create a live output display for streaming responses."""
    from rich.live import Live
    from rich.text import Text
    
    text = Text()
    
    with Live(text, refresh_per_second=10) as live:
        def update_text(new_content: str):
            text.append(new_content)
            live.update(text)
        
        return update_text


def select_multiple_options(
    question: str,
    options: List[str],
    default: List[str] = None
) -> List[str]:
    """Allow selecting multiple options from a list."""
    return questionary.checkbox(
        question,
        choices=options,
        default=default or [],
        style=questionary.Style([
            ('qmark', 'fg:#673ab7 bold'),
            ('question', 'bold'),
            ('answer', 'fg:#f44336 bold'),
            ('pointer', 'fg:#673ab7 bold'),
            ('highlighted', 'fg:#673ab7 bold'),
            ('selected', 'fg:#cc5454'),
        ])
    ).ask() or []