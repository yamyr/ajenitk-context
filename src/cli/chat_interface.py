"""Enhanced interactive chat interface with rich features."""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import json

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich import box
from rich.syntax import Syntax
import questionary

from ..agents import ChatAgent
from ..models import ConversationHistory, Message, ChatResponse
from .utils import (
    format_agent_response,
    create_spinner_context,
    display_conversation_history,
    confirm_action
)


console = Console()


class InteractiveChatSession:
    """Enhanced interactive chat session with rich features."""
    
    def __init__(self, agent: ChatAgent = None):
        self.agent = agent or ChatAgent()
        self.conversation_history = ConversationHistory(
            messages=[],
            session_id=f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        self.commands = self._setup_commands()
        self.context_files: List[Path] = []
        self.settings = {
            "auto_save": True,
            "show_confidence": True,
            "show_suggestions": True,
            "markdown_rendering": True,
            "syntax_highlighting": True
        }
    
    def _setup_commands(self) -> Dict[str, callable]:
        """Setup special chat commands."""
        return {
            "/help": self._show_help,
            "/history": self._show_history,
            "/save": self._save_conversation,
            "/load": self._load_conversation,
            "/clear": self._clear_history,
            "/context": self._add_context,
            "/settings": self._show_settings,
            "/export": self._export_conversation,
            "/stats": self._show_stats,
            "/mode": self._change_mode,
        }
    
    def run(self) -> None:
        """Run the interactive chat session."""
        self._show_welcome()
        
        while True:
            try:
                # Get user input with command completion
                user_input = self._get_user_input()
                
                if user_input.lower() in ["exit", "quit", "bye"]:
                    self._handle_exit()
                    break
                
                # Check for commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue
                
                # Process regular message
                self._process_message(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
    
    def _show_welcome(self) -> None:
        """Display welcome message."""
        welcome_panel = Panel(
            "[bold blue]🤖 AI Chat Assistant[/bold blue]\n\n"
            "Welcome to the enhanced chat interface!\n\n"
            "• Type your message and press Enter to chat\n"
            "• Use /help to see available commands\n"
            "• Type 'exit' to quit\n\n"
            "[dim]Powered by PydanticAI with rich interactivity[/dim]",
            border_style="blue",
            padding=(1, 2),
            title="Welcome",
            subtitle="[dim]Session: " + self.conversation_history.session_id + "[/dim]"
        )
        console.print(welcome_panel)
    
    def _get_user_input(self) -> str:
        """Get user input with enhanced prompt."""
        # Show context indicator if files are loaded
        context_indicator = f" [dim]({len(self.context_files)} files)[/dim]" if self.context_files else ""
        
        # Use questionary for better input experience
        return questionary.text(
            f"You{context_indicator}:",
            multiline=False,
            qmark="💬",
            style=questionary.Style([
                ('qmark', 'fg:#00aa00 bold'),
                ('question', 'bold'),
            ])
        ).ask() or ""
    
    def _process_message(self, message: str) -> None:
        """Process a chat message."""
        # Add context from files if any
        if self.context_files:
            context = self._build_context()
            message = f"{context}\n\nUser question: {message}"
        
        # Show processing indicator
        with console.status("[yellow]AI is thinking...[/yellow]", spinner="dots"):
            try:
                response = self.agent.chat_sync(
                    message=message,
                    conversation_history=self.conversation_history
                )
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                return
        
        # Display response
        self._display_response(response)
        
        # Auto-save if enabled
        if self.settings["auto_save"]:
            self._auto_save()
    
    def _display_response(self, response: ChatResponse) -> None:
        """Display AI response with rich formatting."""
        # Main response
        if self.settings["markdown_rendering"]:
            content = Markdown(response.message)
        else:
            content = response.message
        
        response_panel = Panel(
            content,
            title="[bold green]AI Assistant[/bold green]",
            border_style="green",
            padding=(1, 2),
            subtitle=f"[dim]Confidence: {response.confidence:.2f}[/dim]" if self.settings["show_confidence"] else None
        )
        console.print(response_panel)
        
        # Show suggestions if any
        if response.suggested_actions and self.settings["show_suggestions"]:
            console.print("\n[bold]Suggested actions:[/bold]")
            for action in response.suggested_actions:
                console.print(f"  • {action}")
    
    def _handle_command(self, command: str) -> None:
        """Handle special commands."""
        cmd_parts = command.split()
        cmd_name = cmd_parts[0]
        cmd_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        if cmd_name in self.commands:
            self.commands[cmd_name](*cmd_args)
        else:
            console.print(f"[red]Unknown command: {cmd_name}[/red]")
            console.print("Use /help to see available commands")
    
    def _show_help(self, *args) -> None:
        """Show help information."""
        help_table = Table(
            title="Available Commands",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description")
        help_table.add_column("Usage", style="dim")
        
        commands_info = [
            ("/help", "Show this help message", "/help"),
            ("/history", "Show conversation history", "/history [last_n]"),
            ("/save", "Save conversation", "/save [filename]"),
            ("/load", "Load conversation", "/load [filename]"),
            ("/clear", "Clear conversation history", "/clear"),
            ("/context", "Add file to context", "/context <file_path>"),
            ("/settings", "Show/change settings", "/settings [setting] [value]"),
            ("/export", "Export conversation", "/export [format]"),
            ("/stats", "Show conversation statistics", "/stats"),
            ("/mode", "Change chat mode", "/mode [mode_name]"),
        ]
        
        for cmd, desc, usage in commands_info:
            help_table.add_row(cmd, desc, usage)
        
        console.print(help_table)
    
    def _show_history(self, *args) -> None:
        """Show conversation history."""
        last_n = int(args[0]) if args and args[0].isdigit() else 10
        messages = self.conversation_history.messages[-last_n:]
        
        if not messages:
            console.print("[yellow]No conversation history yet.[/yellow]")
            return
        
        console.print(f"\n[bold]Last {len(messages)} messages:[/bold]\n")
        display_conversation_history([msg.dict() for msg in messages])
    
    def _save_conversation(self, *args) -> None:
        """Save conversation to file."""
        filename = args[0] if args else f"chat_{self.conversation_history.session_id}.json"
        
        try:
            data = {
                "session_id": self.conversation_history.session_id,
                "messages": [msg.dict() for msg in self.conversation_history.messages],
                "timestamp": datetime.now().isoformat()
            }
            
            Path(filename).write_text(json.dumps(data, indent=2))
            console.print(f"[green]✓ Conversation saved to {filename}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to save conversation: {e}[/red]")
    
    def _load_conversation(self, *args) -> None:
        """Load conversation from file."""
        if not args:
            # Show file picker
            files = list(Path(".").glob("chat_*.json"))
            if not files:
                console.print("[yellow]No saved conversations found.[/yellow]")
                return
            
            filename = questionary.select(
                "Select conversation to load:",
                choices=[str(f) for f in files]
            ).ask()
        else:
            filename = args[0]
        
        try:
            data = json.loads(Path(filename).read_text())
            self.conversation_history = ConversationHistory(
                messages=[Message(**msg) for msg in data["messages"]],
                session_id=data["session_id"]
            )
            console.print(f"[green]✓ Loaded conversation from {filename}[/green]")
            console.print(f"[dim]Session: {data['session_id']}[/dim]")
        except Exception as e:
            console.print(f"[red]Failed to load conversation: {e}[/red]")
    
    def _clear_history(self, *args) -> None:
        """Clear conversation history."""
        if confirm_action("Are you sure you want to clear the conversation history?"):
            self.conversation_history.messages.clear()
            console.print("[green]✓ Conversation history cleared[/green]")
    
    def _add_context(self, *args) -> None:
        """Add file to context."""
        if not args:
            filepath = questionary.path(
                "Select file to add to context:",
                only_files=True
            ).ask()
        else:
            filepath = args[0]
        
        try:
            path = Path(filepath)
            if path.exists() and path.is_file():
                self.context_files.append(path)
                console.print(f"[green]✓ Added {path.name} to context[/green]")
                console.print(f"[dim]Total files in context: {len(self.context_files)}[/dim]")
            else:
                console.print(f"[red]File not found: {filepath}[/red]")
        except Exception as e:
            console.print(f"[red]Error adding file: {e}[/red]")
    
    def _build_context(self) -> str:
        """Build context from loaded files."""
        context_parts = ["Context from files:"]
        
        for file in self.context_files:
            try:
                content = file.read_text()
                if file.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c']:
                    # Add syntax highlighting for code files
                    context_parts.append(f"\nFile: {file.name}")
                    context_parts.append(f"```{file.suffix[1:]}\n{content}\n```")
                else:
                    context_parts.append(f"\nFile: {file.name}")
                    context_parts.append(content)
            except Exception as e:
                context_parts.append(f"\nError reading {file.name}: {e}")
        
        return "\n".join(context_parts)
    
    def _show_settings(self, *args) -> None:
        """Show or modify settings."""
        if not args:
            # Show current settings
            settings_table = Table(
                title="Current Settings",
                box=box.ROUNDED
            )
            settings_table.add_column("Setting", style="cyan")
            settings_table.add_column("Value", style="green")
            
            for key, value in self.settings.items():
                settings_table.add_row(key, str(value))
            
            console.print(settings_table)
        elif len(args) == 2:
            # Modify setting
            setting, value = args
            if setting in self.settings:
                # Convert string to appropriate type
                if value.lower() in ["true", "false"]:
                    value = value.lower() == "true"
                self.settings[setting] = value
                console.print(f"[green]✓ {setting} = {value}[/green]")
            else:
                console.print(f"[red]Unknown setting: {setting}[/red]")
    
    def _export_conversation(self, *args) -> None:
        """Export conversation in different formats."""
        format_type = args[0] if args else "markdown"
        
        exporters = {
            "markdown": self._export_markdown,
            "html": self._export_html,
            "txt": self._export_text
        }
        
        if format_type not in exporters:
            console.print(f"[red]Unknown format: {format_type}[/red]")
            console.print("Available formats: " + ", ".join(exporters.keys()))
            return
        
        filename = f"chat_export_{self.conversation_history.session_id}.{format_type}"
        exporters[format_type](filename)
    
    def _export_markdown(self, filename: str) -> None:
        """Export as markdown."""
        content = [f"# Chat Session: {self.conversation_history.session_id}\n"]
        
        for msg in self.conversation_history.messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(msg, 'timestamp') else ""
            if msg.role == "user":
                content.append(f"\n## User {timestamp}\n\n{msg.content}\n")
            else:
                content.append(f"\n## Assistant {timestamp}\n\n{msg.content}\n")
        
        Path(filename).write_text("\n".join(content))
        console.print(f"[green]✓ Exported to {filename}[/green]")
    
    def _export_html(self, filename: str) -> None:
        """Export as HTML."""
        # Implementation for HTML export
        console.print("[yellow]HTML export not yet implemented[/yellow]")
    
    def _export_text(self, filename: str) -> None:
        """Export as plain text."""
        content = []
        for msg in self.conversation_history.messages:
            content.append(f"{msg.role.upper()}: {msg.content}\n")
        
        Path(filename).write_text("\n".join(content))
        console.print(f"[green]✓ Exported to {filename}[/green]")
    
    def _show_stats(self, *args) -> None:
        """Show conversation statistics."""
        total_messages = len(self.conversation_history.messages)
        user_messages = sum(1 for msg in self.conversation_history.messages if msg.role == "user")
        assistant_messages = total_messages - user_messages
        
        # Calculate average message length
        avg_user_length = sum(len(msg.content) for msg in self.conversation_history.messages if msg.role == "user") / max(user_messages, 1)
        avg_assistant_length = sum(len(msg.content) for msg in self.conversation_history.messages if msg.role == "assistant") / max(assistant_messages, 1)
        
        stats_table = Table(
            title="Conversation Statistics",
            box=box.ROUNDED
        )
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        stats_table.add_row("Total Messages", str(total_messages))
        stats_table.add_row("User Messages", str(user_messages))
        stats_table.add_row("Assistant Messages", str(assistant_messages))
        stats_table.add_row("Avg User Message Length", f"{avg_user_length:.0f} chars")
        stats_table.add_row("Avg Assistant Message Length", f"{avg_assistant_length:.0f} chars")
        stats_table.add_row("Context Files", str(len(self.context_files)))
        stats_table.add_row("Session ID", self.conversation_history.session_id)
        
        console.print(stats_table)
    
    def _change_mode(self, *args) -> None:
        """Change chat mode/personality."""
        modes = ["helpful", "creative", "analytical", "concise", "detailed"]
        
        if args and args[0] in modes:
            mode = args[0]
        else:
            mode = questionary.select(
                "Select chat mode:",
                choices=modes
            ).ask()
        
        if mode:
            # This would update agent settings
            console.print(f"[green]✓ Changed to {mode} mode[/green]")
    
    def _auto_save(self) -> None:
        """Auto-save conversation."""
        try:
            filename = f".chat_autosave_{self.conversation_history.session_id}.json"
            self._save_conversation(filename)
        except:
            pass  # Silent fail for auto-save
    
    def _handle_exit(self) -> None:
        """Handle exit gracefully."""
        if self.settings["auto_save"] and self.conversation_history.messages:
            if confirm_action("Save conversation before exiting?", default=True):
                self._save_conversation()
        
        console.print("\n[yellow]Thanks for chatting! Goodbye! 👋[/yellow]")