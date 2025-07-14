# MCP (Model Context Protocol) Integration

Ajentik provides full support for the Model Context Protocol (MCP), enabling seamless integration with Claude Desktop, other MCP-compatible clients, and servers.

## Overview

The MCP integration allows Ajentik to:

1. **Act as an MCP Server** - Expose Ajentik tools to any MCP client
2. **Act as an MCP Client** - Connect to and use tools from any MCP server
3. **Bridge MCP Servers** - Connect multiple MCP servers and share tools between them

## Quick Start

### Using Ajentik as an MCP Server

#### With Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

Or expose specific tool categories:

```json
{
  "mcpServers": {
    "ajentik-files": {
      "command": "ajentik",
      "args": ["mcp", "server", "--categories", "file_system"],
      "env": {}
    }
  }
}
```

#### Command Line

Start an MCP server:

```bash
# Expose all tools
ajentik mcp server

# Expose specific tools
ajentik mcp server --tools read_file --tools write_file

# Expose tool categories
ajentik mcp server --categories file_system --categories data

# With enhanced security
ajentik mcp server --security sandboxed
```

### Using Ajentik as an MCP Client

Connect to any MCP server:

```bash
# Connect to a local server command
ajentik mcp connect "npx @modelcontextprotocol/server-filesystem /path/to/files"

# Connect to a remote server
ajentik mcp connect http://localhost:3000

# Connect and register tools locally
ajentik mcp connect "command" --register --prefix remote
```

## Architecture

### Server Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│  Ajentik MCP    │
│ (Claude, etc)   │     │     Server      │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Tool Registry  │
                        └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
             ┌──────▼──────┐          ┌──────▼──────┐
             │ File Tools  │          │ Data Tools  │
             └─────────────┘          └─────────────┘
```

### Client Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Ajentik Agent  │────▶│  Ajentik MCP    │
│                 │     │     Client      │
└─────────────────┘     └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │   MCP Server    │
                        │  (Any Provider) │
                        └─────────────────┘
```

## MCP Server Features

### Tool Exposure

All Ajentik tools can be exposed via MCP:

- **Built-in Tools**: File system, data processing, etc.
- **Custom Tools**: Any tools created with `@tool` decorator
- **Dynamic Tools**: Tools loaded at runtime

### Security Levels

Control tool access with security levels:

- **unrestricted**: No limitations (use with caution)
- **safe**: Basic safety checks (default)
- **sandboxed**: Resource limits and path restrictions
- **restricted**: Maximum security, limited operations

### Transport Options

- **stdio**: Standard input/output (default, best for local processes)
- **SSE**: Server-Sent Events (for web-based clients)
- **WebSocket**: Full duplex communication (coming soon)

## MCP Client Features

### Tool Discovery

Automatically discover and use tools from any MCP server:

```python
# In Python
client = create_mcp_client(server_command=["npx", "server"])
await client.connect()

# List available tools
tools = await client.list_tools()

# Call a tool
result = await client.call_tool("read_file", {"path": "/tmp/data.txt"})
```

### Local Registration

Register MCP server tools in Ajentik's registry:

```python
# Register all tools with a prefix
await client.register_tools_locally(prefix="remote")

# Now use them like any Ajentik tool
tool = tool_registry.get("remote_read_file")
result = tool(path="/tmp/data.txt")
```

### Resource and Prompt Support

Access MCP resources and prompts:

```python
# List resources
resources = await client.list_resources()

# Read a resource
content = await client.read_resource("file:///path/to/resource")

# Get prompts
prompts = await client.list_prompts()
prompt = await client.get_prompt("code_review", {"language": "python"})
```

## Configuration

### Server Configuration

Create a server configuration file (`mcp_server.json`):

```json
{
  "name": "my-ajentik-server",
  "version": "1.0.0",
  "tools": ["calculator", "file_reader"],
  "categories": ["data"],
  "security_level": "sandboxed",
  "transport": {
    "type": "stdio"
  }
}
```

Use with:

```bash
ajentik mcp server --config mcp_server.json
```

### Client Configuration

Save server configurations:

```bash
# Add a known server
ajentik mcp add-server my-server \
  --command "npx @modelcontextprotocol/server-name" \
  --type "filesystem"

# List known servers
ajentik mcp list-servers

# Connect to saved server
ajentik mcp connect my-server
```

## Advanced Usage

### Custom MCP Server

Create a standalone MCP server script:

```python
#!/usr/bin/env python3
import asyncio
from ajentik.mcp import create_mcp_server
from ajentik.tools import tool

@tool(name="custom_tool")
def my_custom_tool(input: str) -> str:
    return f"Processed: {input}"

async def main():
    server = create_mcp_server(
        name="custom-server",
        tools=[my_custom_tool.tool]
    )
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

### Bidirectional Bridge

Create a bridge between multiple MCP servers:

```python
from ajentik.mcp import MCPClient, create_mcp_server

async def bridge_servers():
    # Connect to external MCP server
    client = MCPClient()
    await client.connect()
    
    # Get tools from external server
    external_tools = await client.list_tools()
    
    # Create Ajentik server exposing both local and external tools
    server = create_mcp_server(
        name="bridge-server",
        # Include local tools and external tools
    )
    
    await server.start()
```

### Tool Filtering and Transformation

Filter and transform tools before exposing:

```python
from ajentik.tools import tool_registry
from ajentik.mcp import create_mcp_server

# Get all file system tools
fs_tools = tool_registry.list_tools(category="file_system")

# Filter for read-only operations
read_only_tools = [
    tool for tool in fs_tools 
    if "read" in tool.name or "list" in tool.name
]

# Create server with filtered tools
server = create_mcp_server(
    name="read-only-fs",
    tools=read_only_tools,
    security_level="restricted"
)
```

## Monitoring and Debugging

### Enable Debug Logging

```bash
# Set logging level
export AJENTIK_LOG_LEVEL=DEBUG

# Start server with debugging
ajentik mcp server --debug
```

### Monitor MCP Traffic

Use the built-in monitoring:

```python
# In server
server.on_notification("message", lambda msg: print(f"Log: {msg}"))

# In client  
client.on_notification("tools/listChanged", lambda _: print("Tools changed!"))
```

## Security Considerations

### Server Security

1. **Use appropriate security levels** - Default to "safe" or higher
2. **Validate inputs** - MCP performs basic validation, but add your own
3. **Limit tool exposure** - Only expose necessary tools
4. **Monitor usage** - Track tool calls and errors

### Client Security

1. **Verify server identity** - Ensure you're connecting to trusted servers
2. **Validate responses** - Check tool results before using
3. **Use sandboxing** - Run untrusted servers in isolated environments

## Troubleshooting

### Common Issues

#### Server won't start
- Check if another process is using the port (for SSE/WebSocket)
- Verify all specified tools exist
- Check security level compatibility

#### Client can't connect
- Ensure server is running
- Check transport compatibility
- Verify network connectivity (for remote servers)

#### Tools not appearing
- Confirm tools are registered in tool registry
- Check security level restrictions
- Verify tool categories match

### Debug Commands

```bash
# Test server locally
ajentik mcp server --tools echo --security unrestricted

# Test client connection
ajentik mcp connect "ajentik mcp server" --no-register

# Validate server configuration
ajentik mcp validate-config server.json
```

## Examples

### Example 1: File Browser Server

```bash
# Expose only file reading tools
ajentik mcp server \
  --tools read_file \
  --tools list_directory \
  --tools file_exists \
  --security safe
```

### Example 2: Data Processing Pipeline

```python
# Connect to data source server
data_client = create_mcp_client(server_command=["data-server"])
await data_client.connect()

# Connect to ML server
ml_client = create_mcp_client(server_url="http://ml-server:3000")
await ml_client.connect()

# Use tools from both servers
data = await data_client.call_tool("fetch_data", {"query": "SELECT *"})
result = await ml_client.call_tool("predict", {"data": data})
```

### Example 3: Multi-Language Integration

```javascript
// Node.js MCP server
const { MCPServer } = require('@modelcontextprotocol/server');

// Connect to Ajentik tools
const ajentikTools = await connectToMCP('ajentik mcp server');

// Use Ajentik tools from JavaScript
const result = await ajentikTools.call('read_file', {
  path: '/tmp/data.json'
});
```

## Best Practices

1. **Start small** - Begin with a few tools and expand
2. **Use categories** - Organize tools logically
3. **Document tools** - Provide clear descriptions
4. **Test thoroughly** - Verify tool behavior across MCP
5. **Monitor usage** - Track performance and errors
6. **Update regularly** - Keep MCP protocol version current

## Integration Examples

### VS Code Extension

```json
{
  "mcp.servers": {
    "ajentik": {
      "command": "ajentik",
      "args": ["mcp", "server", "--categories", "code"],
      "rootPath": "${workspaceFolder}"
    }
  }
}
```

### Web Application

```javascript
// Connect via SSE
const client = new MCPClient({
  url: 'http://localhost:3000/sse',
  transport: 'sse'
});

await client.connect();
const tools = await client.listTools();
```

### CI/CD Pipeline

```yaml
# GitHub Actions
- name: Start Ajentik MCP Server
  run: |
    ajentik mcp server --transport sse --port 3000 &
    echo "MCP_SERVER_URL=http://localhost:3000" >> $GITHUB_ENV

- name: Run MCP Client Tests
  run: |
    npm test -- --mcp-server $MCP_SERVER_URL
```

## Further Resources

- [MCP Specification](https://modelcontextprotocol.io/docs)
- [Ajentik Tools Documentation](TOOLS.md)
- [Security Guide](SECURITY.md)
- [API Reference](API_REFERENCE.md)