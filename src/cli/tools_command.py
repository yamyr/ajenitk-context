"""CLI commands for tool management."""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from ..tools import tool_registry, tool_loader, tool_discovery
from ..tools.validation import ToolValidator, SecurityLevel
from ..tools.documentation import ToolDocumentationGenerator
from .utils import create_spinner_context, confirm_action


console = Console()


@click.group()
def tools():
    """Tool management commands."""
    pass


@tools.command()
@click.option('--category', '-c', help='Filter by category')
@click.option('--search', '-s', help='Search tools by name or description')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed information')
def list(category: str, search: str, detailed: bool):
    """List available tools."""
    # Get tools based on filters
    if search:
        available_tools = tool_registry.search(search)
    elif category:
        available_tools = tool_registry.list_tools(category)
    else:
        available_tools = tool_registry.list_tools()
    
    if not available_tools:
        console.print("[yellow]No tools found matching criteria[/yellow]")
        return
    
    if detailed:
        # Show detailed view
        for tool in available_tools:
            panel_content = f"[cyan]Description:[/cyan] {tool.description}\n"
            panel_content += f"[cyan]Category:[/cyan] {tool.category}\n"
            panel_content += f"[cyan]Version:[/cyan] {tool.version}\n"
            panel_content += f"[cyan]Author:[/cyan] {tool.author}\n"
            panel_content += f"[cyan]Safe:[/cyan] {'✓' if tool.is_safe else '✗'}\n"
            panel_content += f"[cyan]Requires Confirmation:[/cyan] {'✓' if tool.requires_confirmation else '✗'}\n"
            
            if tool.parameters():
                panel_content += "\n[cyan]Parameters:[/cyan]\n"
                for param in tool.parameters():
                    req = "[red]*[/red]" if param.required else ""
                    panel_content += f"  • {param.name}{req} ({param.type.value}): {param.description}\n"
            
            console.print(Panel(
                panel_content,
                title=f"🔧 {tool.name}",
                border_style="blue"
            ))
            console.print()
    else:
        # Show table view
        table = Table(title="Available Tools", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="yellow")
        table.add_column("Description")
        table.add_column("Safe", justify="center")
        table.add_column("Confirm", justify="center")
        
        for tool in available_tools:
            table.add_row(
                tool.name,
                tool.category,
                tool.description[:50] + "..." if len(tool.description) > 50 else tool.description,
                "✓" if tool.is_safe else "✗",
                "✓" if tool.requires_confirmation else "✗"
            )
        
        console.print(table)
    
    # Show statistics
    stats = tool_registry.get_statistics()
    console.print(f"\n[dim]Total tools: {stats['total_tools']} | "
                 f"Categories: {stats['total_categories']} | "
                 f"Safe tools: {stats['safe_tools']}[/dim]")


@tools.command()
@click.argument('tool_name')
@click.option('--params', '-p', multiple=True, help='Parameters as key=value pairs')
@click.option('--json', 'output_json', is_flag=True, help='Output result as JSON')
@click.option('--no-confirm', is_flag=True, help='Skip confirmation prompts')
def run(tool_name: str, params: tuple, output_json: bool, no_confirm: bool):
    """Execute a tool."""
    tool = tool_registry.get(tool_name)
    if not tool:
        console.print(f"[red]Tool '{tool_name}' not found[/red]")
        return
    
    # Parse parameters
    kwargs = {}
    for param in params:
        if '=' not in param:
            console.print(f"[red]Invalid parameter format: {param} (use key=value)[/red]")
            return
        key, value = param.split('=', 1)
        
        # Try to parse value types
        if value.lower() in ['true', 'false']:
            kwargs[key] = value.lower() == 'true'
        elif value.isdigit():
            kwargs[key] = int(value)
        else:
            try:
                kwargs[key] = float(value)
            except ValueError:
                kwargs[key] = value
    
    # Show tool info and confirm if needed
    if tool.requires_confirmation and not no_confirm:
        console.print(Panel(
            f"[yellow]Tool: {tool.name}[/yellow]\n"
            f"Description: {tool.description}\n"
            f"Parameters: {kwargs}",
            title="⚠️  Confirmation Required",
            border_style="yellow"
        ))
        
        if not confirm_action("Proceed with tool execution?"):
            console.print("[red]Execution cancelled[/red]")
            return
    
    # Execute tool
    with create_spinner_context(f"Executing {tool_name}..."):
        try:
            result = tool(**kwargs)
        except Exception as e:
            console.print(f"[red]Error executing tool: {e}[/red]")
            return
    
    # Display result
    if output_json:
        import json
        console.print_json(json.dumps(result.dict(), default=str))
    else:
        if result.success:
            console.print(Panel(
                f"[green]✓ Success[/green]\n\n"
                f"Data: {result.data}",
                title=f"Tool Result: {tool_name}",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[red]✗ Failed[/red]\n\n"
                f"Error: {result.error}",
                title=f"Tool Result: {tool_name}",
                border_style="red"
            ))
        
        if result.metadata:
            console.print(f"\n[dim]Metadata: {result.metadata}[/dim]")
        if result.execution_time:
            console.print(f"[dim]Execution time: {result.execution_time:.2f}s[/dim]")


@tools.command()
@click.argument('path', type=click.Path())
@click.option('--type', '-t', 'load_type', 
              type=click.Choice(['file', 'directory', 'module', 'config']),
              help='Type of path to load from')
@click.option('--recursive', '-r', is_flag=True, help='Load recursively from directories')
def load(path: str, load_type: str, recursive: bool):
    """Load tools from various sources."""
    path_obj = Path(path)
    
    with create_spinner_context(f"Loading tools from {path}..."):
        try:
            if load_type == 'file' or (not load_type and path_obj.suffix == '.py'):
                count = tool_loader.load_from_file(path_obj)
            elif load_type == 'directory' or (not load_type and path_obj.is_dir()):
                count = tool_loader.load_from_directory(path_obj, recursive)
            elif load_type == 'module':
                count = tool_loader.load_from_module(path)
            elif load_type == 'config' or (not load_type and path_obj.suffix in ['.yaml', '.yml', '.json']):
                count = tool_loader.load_from_config(path_obj)
            else:
                console.print("[red]Could not determine load type[/red]")
                return
            
            console.print(f"[green]✓ Loaded {count} tools from {path}[/green]")
            
        except Exception as e:
            console.print(f"[red]Error loading tools: {e}[/red]")


@tools.command()
@click.option('--builtin/--no-builtin', default=True, help='Load built-in tools')
@click.option('--search-paths/--no-search-paths', default=True, help='Search default paths')
def discover(builtin: bool, search_paths: bool):
    """Discover and load all available tools."""
    results = {}
    
    with create_spinner_context("Discovering tools..."):
        if builtin:
            count = tool_loader.load_builtin_tools()
            results["Built-in tools"] = count
        
        if search_paths:
            discovery_results = tool_discovery.discover_all()
            results.update(discovery_results)
    
    # Display results
    table = Table(title="Tool Discovery Results", box=box.ROUNDED)
    table.add_column("Source", style="cyan")
    table.add_column("Tools Loaded", justify="right", style="green")
    
    total = 0
    for source, count in results.items():
        table.add_row(source, str(count))
        total += count
    
    table.add_row("", "")
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")
    
    console.print(table)


@tools.command()
@click.argument('tool_name')
@click.option('--level', '-l', 
              type=click.Choice(['unrestricted', 'safe', 'sandboxed', 'restricted']),
              default='safe',
              help='Security level for validation')
def validate(tool_name: str, level: str):
    """Validate a tool for safety and correctness."""
    tool = tool_registry.get(tool_name)
    if not tool:
        console.print(f"[red]Tool '{tool_name}' not found[/red]")
        return
    
    # Create validator
    security_level = SecurityLevel(level)
    validator = ToolValidator(security_level)
    
    # Validate tool
    with create_spinner_context(f"Validating {tool_name}..."):
        results = validator.validate_tool(tool)
    
    # Display results
    if results['valid']:
        console.print(Panel(
            f"[green]✓ Tool is valid[/green]\n\n"
            f"Security Level: {security_level.value}",
            title=f"Validation Passed: {tool_name}",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[red]✗ Tool validation failed[/red]\n\n"
            f"Security Level: {security_level.value}",
            title=f"Validation Failed: {tool_name}",
            border_style="red"
        ))
    
    # Show errors
    if results['errors']:
        console.print("\n[red]Errors:[/red]")
        for error in results['errors']:
            console.print(f"  • {error}")
    
    # Show warnings
    if results['warnings']:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in results['warnings']:
            console.print(f"  • {warning}")


@tools.command()
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--format', '-f', 'formats', 
              multiple=True,
              type=click.Choice(['markdown', 'html', 'json', 'openapi']),
              help='Documentation formats to generate')
@click.option('--category', '-c', help='Document only tools in this category')
def docs(output: str, formats: tuple, category: str):
    """Generate tool documentation."""
    output_dir = Path(output or './docs/tools')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get tools to document
    if category:
        tools_to_doc = tool_registry.list_tools(category)
    else:
        tools_to_doc = None
    
    # Default formats if none specified
    if not formats:
        formats = ['markdown', 'html']
    
    doc_gen = ToolDocumentationGenerator()
    
    with create_spinner_context("Generating documentation..."):
        results = doc_gen.write_documentation(
            output_dir,
            list(formats),
            tools_to_doc
        )
    
    console.print(Panel(
        "\n".join([f"[green]✓[/green] {fmt.title()}: {path}" for fmt, path in results.items()]),
        title="Documentation Generated",
        border_style="green"
    ))


@tools.command()
def stats():
    """Show tool registry statistics."""
    stats = tool_registry.get_statistics()
    
    # Create statistics table
    table = Table(title="Tool Registry Statistics", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    table.add_row("Total Tools", str(stats['total_tools']))
    table.add_row("Categories", str(stats['total_categories']))
    table.add_row("Aliases", str(stats['total_aliases']))
    table.add_row("Async Tools", str(stats['async_tools']))
    table.add_row("Safe Tools", str(stats['safe_tools']))
    table.add_row("Tools Requiring Confirmation", str(stats['tools_requiring_confirmation']))
    
    console.print(table)
    
    # Show tools by category
    if stats['tools_by_category']:
        console.print("\n[cyan]Tools by Category:[/cyan]")
        for category, count in stats['tools_by_category'].items():
            console.print(f"  • {category}: {count}")


# Add tools command to main CLI
def add_tools_command(cli):
    """Add tools command to the main CLI."""
    cli.add_command(tools)