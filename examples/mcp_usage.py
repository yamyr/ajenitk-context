"""Example of using MCP client and server in Python."""

import asyncio
from pathlib import Path

from src.mcp import MCPServer, MCPClient, create_mcp_server, create_mcp_client
from src.tools import tool, tool_registry
from src.tools.validation import SecurityLevel


# Define some example tools
@tool(name="get_time", description="Get current time")
def get_current_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(name="echo", description="Echo back the input")
def echo_message(message: str) -> str:
    """Echo back the provided message."""
    return f"Echo: {message}"


async def server_example():
    """Example of running an MCP server."""
    print("Starting MCP Server Example")
    
    # Create server with specific tools
    server = create_mcp_server(
        name="example-server",
        version="1.0.0",
        tools=[get_current_time.tool, echo_message.tool],
        security_level=SecurityLevel.SAFE
    )
    
    # In a real scenario, the server would run indefinitely
    # Here we'll just show it's created
    print(f"Server created: {server.name}")
    print(f"Exposed tools: {[t.name for t in [get_current_time.tool, echo_message.tool]]}")


async def client_example():
    """Example of using an MCP client."""
    print("\nMCP Client Example")
    
    # In a real scenario, you would connect to an actual server
    # For this example, we'll show the client API
    
    # Create client (would normally connect to a server)
    # client = create_mcp_client(
    #     server_command=["ajentik", "mcp", "server"],
    #     transport_type="stdio"
    # )
    
    # Example of what you would do with a connected client:
    """
    # Connect to server
    await client.connect()
    
    # Get server info
    info = client.get_server_info()
    print(f"Connected to: {info}")
    
    # List available tools
    tools = await client.list_tools()
    print(f"Available tools: {[t['name'] for t in tools]}")
    
    # Call a tool
    result = await client.call_tool("get_time")
    print(f"Current time: {result.content}")
    
    # Register tools locally
    await client.register_tools_locally(prefix="remote")
    
    # Now you can use remote tools through Ajentik's tool registry
    remote_time = tool_registry.get("remote_get_time")
    if remote_time:
        result = remote_time()
        print(f"Time via registry: {result.data}")
    
    # Disconnect
    await client.disconnect()
    """
    
    print("(Client example code shown - requires running server)")


async def bidirectional_example():
    """Example of Ajentik acting as both client and server."""
    print("\nBidirectional MCP Example")
    
    # Ajentik can be both a server (exposing its tools)
    # and a client (using tools from other MCP servers)
    
    # As a server: Expose Ajentik tools to other MCP clients
    server_task = """
    server = create_mcp_server(
        categories=["file_system", "data"],
        security_level=SecurityLevel.SANDBOXED
    )
    await server.start()
    """
    
    # As a client: Connect to other MCP servers
    client_task = """
    client = create_mcp_client(
        server_url="http://localhost:3000",
        transport_type="sse"
    )
    await client.connect()
    
    # Use remote tools
    remote_tools = await client.list_tools()
    
    # Register them locally for agents to use
    await client.register_tools_locally()
    """
    
    print("Ajentik can simultaneously:")
    print("1. Expose its tools as an MCP server")
    print("2. Connect to other MCP servers as a client")
    print("3. Bridge tools between different MCP servers")


def integration_with_claude():
    """Show how to integrate with Claude Desktop."""
    print("\nClaude Desktop Integration")
    
    claude_config = """
    Add to Claude Desktop configuration:
    
    {
      "mcpServers": {
        "ajentik": {
          "command": "ajentik",
          "args": ["mcp", "server", "--categories", "file_system"],
          "env": {}
        }
      }
    }
    
    Or use the Python script directly:
    
    {
      "mcpServers": {
        "ajentik-custom": {
          "command": "python",
          "args": ["-m", "src.mcp.server_script"],
          "env": {
            "PYTHONPATH": "/path/to/ajentik"
          }
        }
      }
    }
    """
    
    print(claude_config)


async def main():
    """Run all examples."""
    await server_example()
    await client_example()
    await bidirectional_example()
    integration_with_claude()
    
    print("\nMCP Integration Summary:")
    print("- Ajentik tools can be exposed via MCP to any compatible client")
    print("- Ajentik can connect to and use tools from any MCP server")
    print("- Full bidirectional compatibility with the MCP ecosystem")
    print("- Seamless integration with Claude Desktop and other MCP clients")


if __name__ == "__main__":
    asyncio.run(main()