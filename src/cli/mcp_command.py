"""CLI commands for MCP integration."""

import click
import asyncio
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.syntax import Syntax

from ..mcp import MCPServer, MCPClient, create_mcp_server, create_mcp_client
from ..mcp.transport import StdioTransport, SSETransport
from ..tools import tool_registry
from ..tools.validation import SecurityLevel
from .utils import create_spinner_context, confirm_action, create_file_tree


console = Console()


@click.group()
def mcp():
    """MCP (Model Context Protocol) commands."""
    pass


@mcp.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', type=int, default=3000, help='Port for HTTP/SSE transport')
@click.option('--transport', type=click.Choice(['stdio', 'sse']), default='stdio', help='Transport type')
@click.option('--tools', '-t', multiple=True, help='Specific tools to expose')
@click.option('--categories', '-c', multiple=True, help='Tool categories to expose')
@click.option('--security', type=click.Choice(['unrestricted', 'safe', 'sandboxed', 'restricted']), 
              default='safe', help='Security level')
@click.option('--config', type=click.Path(exists=True), help='Configuration file')
def server(host: str, port: int, transport: str, tools: tuple, categories: tuple, security: str, config: str):
    """Start an MCP server to expose Ajentik tools."""
    console.print(Panel(
        f"[bold]Starting Ajentik MCP Server[/bold]\n"
        f"Transport: {transport}\n"
        f"Security: {security}",
        title="🚀 MCP Server",
        border_style="blue"
    ))
    
    # Load configuration if provided
    server_config = {}
    if config:
        config_path = Path(config)
        if config_path.suffix in ['.json', '.yaml', '.yml']:
            with open(config_path) as f:
                if config_path.suffix == '.json':
                    server_config = json.load(f)
                else:
                    import yaml
                    server_config = yaml.safe_load(f)
    
    # Get specific tools if requested
    tool_list = None
    if tools:
        tool_list = []
        for tool_name in tools:
            tool = tool_registry.get(tool_name)
            if tool:
                tool_list.append(tool)
            else:
                console.print(f"[yellow]Warning: Tool '{tool_name}' not found[/yellow]")
    
    # Create server
    security_level = SecurityLevel(security)
    
    async def run_server():
        # Create transport
        if transport == 'stdio':
            transport_obj = StdioTransport()
        else:  # sse
            # For SSE, we need to create an HTTP server
            from aiohttp import web
            
            app = web.Application()
            transport_obj = None  # Will be created per connection
            
            # Create MCP server instance
            server = create_mcp_server(
                tools=tool_list,
                categories=list(categories) if categories else None,
                security_level=security_level,
                **server_config
            )
            
            # SSE endpoint
            async def sse_handler(request):
                response = web.StreamResponse()
                response.headers['Content-Type'] = 'text/event-stream'
                response.headers['Cache-Control'] = 'no-cache'
                response.headers['Connection'] = 'keep-alive'
                await response.prepare(request)
                
                # Handle SSE connection
                # ... SSE implementation ...
                
                return response
            
            # Add routes
            app.router.add_get('/sse', sse_handler)
            app.router.add_post('/rpc', lambda req: web.json_response({"status": "ok"}))
            
            # Start web server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            
            console.print(f"[green]✓ SSE server running at http://{host}:{port}[/green]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")
            
            # Keep running
            await asyncio.Event().wait()
            
        else:
            # Stdio transport
            server = create_mcp_server(
                tools=tool_list,
                categories=list(categories) if categories else None,
                security_level=security_level,
                transport=transport_obj,
                **server_config
            )
            
            # Show available tools
            available_tools = tool_registry.list_tools()
            if tool_list:
                available_tools = tool_list
            elif categories:
                available_tools = []
                for cat in categories:
                    available_tools.extend(tool_registry.list_tools(cat))
            
            table = Table(title="Exposed Tools", box=box.ROUNDED)
            table.add_column("Tool", style="cyan")
            table.add_column("Category", style="yellow")
            table.add_column("Description")
            
            for tool in available_tools[:10]:  # Show first 10
                table.add_row(
                    tool.name,
                    tool.category,
                    tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
                )
            
            if len(available_tools) > 10:
                table.add_row("...", f"({len(available_tools) - 10} more)", "...")
            
            console.print(table)
            console.print(f"\n[green]✓ Server ready with {len(available_tools)} tools[/green]")
            console.print("[dim]Waiting for client connections...[/dim]")
            
            # Start server
            await server.start()
    
    # Run server
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@mcp.command()
@click.argument('server_spec')
@click.option('--transport', type=click.Choice(['stdio', 'sse', 'websocket']), help='Transport type')
@click.option('--register/--no-register', default=True, help='Register tools locally')
@click.option('--prefix', default='mcp', help='Prefix for registered tools')
def connect(server_spec: str, transport: str, register: bool, prefix: str):
    """Connect to an MCP server.
    
    SERVER_SPEC can be:
    - A command to launch (for stdio): "npx @modelcontextprotocol/server-name"  
    - A URL (for SSE/WebSocket): "http://localhost:3000"
    - A config file path: "server.json"
    """
    console.print(Panel(
        f"[bold]Connecting to MCP Server[/bold]\n"
        f"Server: {server_spec}",
        title="🔌 MCP Client",
        border_style="green"
    ))
    
    async def run_client():
        # Determine transport type and create client
        if server_spec.startswith(('http://', 'https://', 'ws://', 'wss://')):
            # URL - use SSE or WebSocket
            if not transport:
                transport = 'sse' if server_spec.startswith('http') else 'websocket'
            
            client = create_mcp_client(
                server_url=server_spec,
                transport_type=transport
            )
        elif Path(server_spec).exists() and Path(server_spec).suffix in ['.json', '.yaml']:
            # Config file
            with open(server_spec) as f:
                if Path(server_spec).suffix == '.json':
                    config = json.load(f)
                else:
                    import yaml
                    config = yaml.safe_load(f)
            
            client = create_mcp_client(**config)
        else:
            # Command - use stdio
            import shlex
            command = shlex.split(server_spec)
            
            client = create_mcp_client(
                server_command=command,
                transport_type='stdio'
            )
        
        # Connect to server
        with create_spinner_context("Connecting to server..."):
            await client.connect()
        
        # Get server info
        server_info = client.get_server_info()
        capabilities = client.get_server_capabilities()
        
        console.print(Panel(
            f"[green]✓ Connected to {server_info.get('name', 'Unknown')} "
            f"v{server_info.get('version', 'Unknown')}[/green]\n\n"
            f"Capabilities:\n"
            f"  Tools: {'✓' if client.supports_tools() else '✗'}\n"
            f"  Resources: {'✓' if client.supports_resources() else '✗'}\n"
            f"  Prompts: {'✓' if client.supports_prompts() else '✗'}",
            title="Server Info",
            border_style="green"
        ))
        
        # List available tools
        if client.supports_tools():
            tools = await client.list_tools()
            
            table = Table(title="Available Tools", box=box.ROUNDED)
            table.add_column("Name", style="cyan")
            table.add_column("Description")
            
            for tool in tools[:10]:
                table.add_row(
                    tool['name'],
                    tool.get('description', 'No description')[:60] + "..."
                )
            
            if len(tools) > 10:
                table.add_row("...", f"({len(tools) - 10} more tools)")
            
            console.print(table)
            
            # Register tools locally if requested
            if register:
                with create_spinner_context(f"Registering {len(tools)} tools locally..."):
                    await client.register_tools_locally(prefix=prefix)
                
                console.print(f"[green]✓ Registered {len(tools)} tools with prefix '{prefix}'[/green]")
        
        # Interactive mode
        console.print("\n[bold]Interactive MCP Client[/bold]")
        console.print("Commands: tools, resources, prompts, call <tool>, read <uri>, exit")
        
        while True:
            try:
                command = console.input("\n[cyan]mcp>[/cyan] ")
                
                if command == "exit":
                    break
                elif command == "tools":
                    tools = await client.list_tools()
                    for tool in tools:
                        console.print(f"  • {tool['name']}: {tool.get('description', '')}")
                elif command == "resources":
                    if client.supports_resources():
                        resources = await client.list_resources()
                        for res in resources:
                            console.print(f"  • {res['uri']}: {res.get('name', '')}")
                    else:
                        console.print("[yellow]Server does not support resources[/yellow]")
                elif command == "prompts":
                    if client.supports_prompts():
                        prompts = await client.list_prompts()
                        for prompt in prompts:
                            console.print(f"  • {prompt['name']}: {prompt.get('description', '')}")
                    else:
                        console.print("[yellow]Server does not support prompts[/yellow]")
                elif command.startswith("call "):
                    tool_name = command[5:]
                    # Simple argument input
                    args_str = console.input("Arguments (JSON): ")
                    args = json.loads(args_str) if args_str else {}
                    
                    result = await client.call_tool(tool_name, args)
                    console.print(Panel(
                        json.dumps(result.dict(), indent=2),
                        title=f"Tool Result: {tool_name}",
                        border_style="green" if not result.isError else "red"
                    ))
                elif command.startswith("read "):
                    uri = command[5:]
                    if client.supports_resources():
                        result = await client.read_resource(uri)
                        console.print(Panel(
                            json.dumps(result.dict(), indent=2),
                            title=f"Resource: {uri}",
                            border_style="blue"
                        ))
                    else:
                        console.print("[yellow]Server does not support resources[/yellow]")
                else:
                    console.print("[yellow]Unknown command[/yellow]")
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        # Disconnect
        await client.disconnect()
        console.print("[yellow]Disconnected from server[/yellow]")
    
    # Run client
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        console.print("\n[yellow]Client disconnected[/yellow]")


@mcp.command()
@click.option('--format', type=click.Choice(['json', 'yaml']), default='json', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file')
def list_servers(format: str, output: str):
    """List known MCP servers."""
    # Load known servers from config
    config_path = Path.home() / ".ajentik" / "mcp_servers.json"
    
    servers = []
    if config_path.exists():
        with open(config_path) as f:
            servers = json.load(f)
    
    if not servers:
        console.print("[yellow]No known MCP servers[/yellow]")
        console.print("\nAdd servers using: ajentik mcp add-server")
        return
    
    # Display servers
    table = Table(title="Known MCP Servers", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Location")
    table.add_column("Transport")
    
    for server in servers:
        table.add_row(
            server['name'],
            server.get('type', 'unknown'),
            server.get('command', server.get('url', 'N/A')),
            server.get('transport', 'stdio')
        )
    
    console.print(table)
    
    # Save to file if requested
    if output:
        output_path = Path(output)
        if format == 'json':
            output_path.write_text(json.dumps(servers, indent=2))
        else:
            import yaml
            output_path.write_text(yaml.dump(servers))
        console.print(f"\n[green]✓ Saved to {output}[/green]")


@mcp.command()
@click.argument('name')
@click.option('--command', help='Command to launch server')
@click.option('--url', help='Server URL')
@click.option('--transport', type=click.Choice(['stdio', 'sse', 'websocket']), help='Transport type')
@click.option('--type', 'server_type', help='Server type/description')
def add_server(name: str, command: str, url: str, transport: str, server_type: str):
    """Add a known MCP server configuration."""
    if not command and not url:
        console.print("[red]Error: Either --command or --url must be provided[/red]")
        return
    
    # Load existing servers
    config_path = Path.home() / ".ajentik" / "mcp_servers.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    servers = []
    if config_path.exists():
        with open(config_path) as f:
            servers = json.load(f)
    
    # Check if server already exists
    for server in servers:
        if server['name'] == name:
            if not confirm_action(f"Server '{name}' already exists. Replace?"):
                return
            servers.remove(server)
            break
    
    # Add new server
    server_config = {
        'name': name,
        'type': server_type or 'custom'
    }
    
    if command:
        server_config['command'] = command
        server_config['transport'] = transport or 'stdio'
    else:
        server_config['url'] = url
        server_config['transport'] = transport or ('sse' if url.startswith('http') else 'websocket')
    
    servers.append(server_config)
    
    # Save configuration
    config_path.write_text(json.dumps(servers, indent=2))
    
    console.print(Panel(
        f"[green]✓ Added MCP server '{name}'[/green]\n\n"
        f"Connect with: ajentik mcp connect {name}",
        title="Server Added",
        border_style="green"
    ))


@mcp.command()
def docs():
    """Show MCP documentation and examples."""
    doc_content = """
# MCP (Model Context Protocol) Integration

The Ajentik framework supports both MCP server and client functionality,
allowing seamless integration with the MCP ecosystem.

## Starting an MCP Server

Expose your Ajentik tools as an MCP server:

```bash
# Start with stdio transport (default)
ajentik mcp server

# Start with specific tools
ajentik mcp server --tools calculator --tools file_reader

# Start with tool categories
ajentik mcp server --categories file_system --categories data

# Start with SSE transport
ajentik mcp server --transport sse --port 3000
```

## Connecting to MCP Servers

Connect to any MCP-compatible server:

```bash
# Connect to a local command
ajentik mcp connect "npx @modelcontextprotocol/server-everything"

# Connect to a remote server
ajentik mcp connect http://localhost:3000

# Connect and register tools locally
ajentik mcp connect "npx server" --prefix remote
```

## Configuration Files

Create server configurations in JSON or YAML:

```json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "tools": ["calculator", "file_reader"],
  "security_level": "safe",
  "transport": {
    "type": "stdio"
  }
}
```

## Security Levels

- **unrestricted**: No security checks
- **safe**: Basic safety validation (default)
- **sandboxed**: Full sandboxing with limits
- **restricted**: Maximum security

## Examples

### Expose Python Tools

```python
from ajentik.tools import tool

@tool(name="hello", description="Say hello")
def say_hello(name: str) -> str:
    return f"Hello, {name}!"

# This tool is now available via MCP
```

### Connect from Claude Desktop

Add to Claude Desktop config:

```json
{
  "mcpServers": {
    "ajentik": {
      "command": "ajentik",
      "args": ["mcp", "server"],
      "env": {}
    }
  }
}
```
"""
    
    syntax = Syntax(doc_content, "markdown", theme="monokai")
    console.print(Panel(syntax, title="MCP Documentation", border_style="blue"))


# Add MCP command to main CLI
def add_mcp_command(cli):
    """Add MCP command to the main CLI."""
    cli.add_command(mcp)