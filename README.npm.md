# Ajentik MCP - Model Context Protocol Tools

[![npm version](https://badge.fury.io/js/ajentik-mcp.svg)](https://www.npmjs.com/package/ajentik-mcp)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Ajentik MCP provides a powerful Model Context Protocol (MCP) server and client implementation, enabling seamless integration of development tools with AI assistants like Claude Desktop.

## Features

- 🚀 **MCP Server** - Expose your tools via Model Context Protocol
- 🔧 **Built-in Tools** - File system operations, code analysis, and more
- 🔌 **Easy Integration** - Works with Claude Desktop out of the box
- 🛡️ **Security Levels** - Control tool execution permissions
- 📦 **Extensible** - Create custom tools with simple decorators
- 🌐 **Multiple Transports** - stdio and Server-Sent Events (SSE)

## Prerequisites

- Node.js 16.0.0 or higher
- Python 3.9 or higher
- pip (Python package installer)

## Installation

```bash
npm install -g ajentik-mcp
```

The post-install script will automatically set up Python dependencies.

## Quick Start

### 1. Start MCP Server

```bash
# Start with default settings
ajentik-mcp server

# Start with specific options
ajentik-mcp server --transport stdio --security safe
```

### 2. Configure Claude Desktop

```bash
# Automatically configure Claude Desktop
ajentik-mcp configure
```

This adds Ajentik to your Claude Desktop configuration. Restart Claude Desktop to use Ajentik tools.

### 3. List Available Tools

```bash
ajentik-mcp list-tools
```

## Usage Examples

### CLI Commands

```bash
# Start MCP server with stdio transport (default)
ajentik-mcp server

# Start MCP server with SSE transport on port 3000
ajentik-mcp server --transport sse --port 3000

# Connect to another MCP server
ajentik-mcp connect "command-to-start-server"

# Show information
ajentik-mcp info
```

### Programmatic Usage

```javascript
const { AjentikMCP } = require('ajentik-mcp');

async function startServer() {
  const server = new AjentikMCP({
    transport: 'stdio',
    security: 'safe',
    categories: 'file_system,development'
  });
  
  await server.startServer();
  console.log('MCP server is running');
}

startServer();
```

### In package.json Scripts

```json
{
  "scripts": {
    "mcp": "ajentik-mcp server",
    "mcp:dev": "ajentik-mcp server --security safe --discover"
  }
}
```

## Available Tools

Ajentik MCP includes various built-in tools:

- **File System Tools**
  - `read_file` - Read file contents
  - `write_file` - Write to files
  - `list_directory` - List directory contents
  - `create_directory` - Create directories
  - `delete_file` - Delete files
  - `file_exists` - Check file existence
  - `get_file_info` - Get file metadata

- **Development Tools**
  - Code analysis
  - Project structure analysis
  - Test generation
  - Documentation generation

## Security Levels

Control tool execution with security levels:

- `unrestricted` - All tools available (use with caution)
- `safe` - Default, excludes potentially dangerous operations
- `sandboxed` - Limited file system access
- `restricted` - Minimal tool set

```bash
ajentik-mcp server --security sandboxed
```

## Creating Custom Tools

Create project-specific tools by adding them to your project:

```python
# .ajentik/custom_tools.py
from ajentik.tools import tool

@tool(name="project_build", description="Build the project")
def build_project(target: str = "all") -> dict:
    """Build project targets."""
    # Implementation here
    return {"status": "success", "target": target}
```

Then start the server with auto-discovery:

```bash
ajentik-mcp server --discover
```

## Troubleshooting

### Python Not Found

If you get a "Python not found" error:

**Windows:**
- Install Python from [python.org](https://python.org) or Microsoft Store
- Make sure to check "Add Python to PATH" during installation

**macOS:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt-get install python3 python3-pip
```

### Permission Errors

If you encounter permission errors during installation:

```bash
# Try with unsafe-perm flag
npm install -g ajentik-mcp --unsafe-perm

# Or use a Node version manager like nvm
```

### Module Import Errors

If Python modules aren't found:

```bash
# Install Python package directly
pip install ajentik-context
```

## Development

To contribute or modify Ajentik MCP:

```bash
# Clone the repository
git clone https://github.com/yourusername/ajentik-context.git
cd ajentik-context

# Install in development mode
npm install
npm link

# Run tests
npm test
```

## License

MIT License - see LICENSE file for details.

## Links

- [GitHub Repository](https://github.com/yourusername/ajentik-context)
- [NPM Package](https://www.npmjs.com/package/ajentik-mcp)
- [Documentation](https://github.com/yourusername/ajentik-context/wiki)
- [Issue Tracker](https://github.com/yourusername/ajentik-context/issues)

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/yourusername/ajentik-context/issues).