# Ajenitk Context - Ajentik AI System

A powerful, modular ajentik AI system built with PydanticAI and enhanced with Logfire monitoring. This system provides autonomous agents for chat, code generation, and code analysis with rich CLI interactivity and comprehensive observability.

## Features

- **🤖 Multiple Specialized Agents**
  - **ChatAgent**: Interactive conversational AI with memory management
  - **CodeAgent**: Intelligent code generation across multiple languages
  - **AnalysisAgent**: Comprehensive code analysis for quality, security, and performance

- **🎨 Rich CLI Interface**
  - Enhanced terminal UI with colors and animations
  - Interactive menus and file browsers
  - Real-time progress indicators
  - Markdown rendering in terminal

- **📊 Comprehensive Monitoring**
  - Real-time metrics dashboard
  - Performance tracking and alerts
  - Token usage and cost monitoring
  - Distributed tracing with Logfire

- **🔧 Flexible Architecture**
  - Support for multiple AI providers (OpenAI, Anthropic, Google)
  - Modular design with dependency injection
  - Async-first with sync compatibility
  - Extensible tool system with sandboxing

- **🔨 Powerful Tool System**
  - Dynamic tool loading and discovery
  - Built-in file system tools
  - Custom tool creation with decorators
  - Security validation and sandboxing
  - Auto-generated documentation

- **🔌 MCP (Model Context Protocol) Support**
  - Full MCP server implementation
  - MCP client for connecting to any MCP server
  - Seamless Claude Desktop integration
  - Tool bridging between MCP servers
  - Multiple transport protocols (stdio, SSE)

## Quick Start

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ajenitk-context.git
   cd ajenitk-context
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Install the CLI:**
   ```bash
   pip install -e .
   ```

### Basic Usage

```bash
# Interactive chat
ajentik chat --enhanced

# Generate code
ajentik code generate -l python

# Analyze code
ajentik code analyze script.py

# View monitoring dashboard
ajentik monitor --live

# Manage tools
ajentik tools list
ajentik tools run calculator --params expression="2+2"

# MCP server/client
ajentik mcp server --categories file_system
ajentik mcp connect "npx @modelcontextprotocol/server-name"

# Configure settings
ajentik config
```

## Configuration

Create a `.env` file with your API keys:

```env
# AI Provider Keys (at least one required)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key

# Monitoring (optional)
LOGFIRE_WRITE_TOKEN=your-logfire-token
LOGFIRE_PROJECT=your-project-name

# Model Settings
DEFAULT_MODEL=openai:gpt-4o
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=1000
```

## Examples

### Chat with Context

```python
from src.agents import ChatAgent
from src.models import ConversationHistory

agent = ChatAgent()
history = ConversationHistory(messages=[], session_id="my-session")

response = await agent.chat(
    "Explain Python decorators",
    conversation_history=history
)
print(response.message)
```

### Generate Code

```python
from src.agents import CodeAgent
from src.models import CodeGenerationRequest

agent = CodeAgent()
request = CodeGenerationRequest(
    description="Create a REST API endpoint",
    language="python",
    framework="fastapi",
    requirements=["Include authentication", "Add input validation"]
)

response = await agent.generate_code(request)
print(response.code)
```

### Analyze Code

```python
from src.agents import AnalysisAgent
from src.models import CodeAnalysisRequest

agent = AnalysisAgent()
request = CodeAnalysisRequest(
    code=open("script.py").read(),
    language="python",
    analysis_types=["security", "quality", "performance"]
)

response = await agent.analyze_code(request)
print(f"Score: {response.overall_score}/10")
for issue in response.issues:
    print(f"- {issue.description}")
```

## Project Structure

```
ajenitk-context/
├── src/
│   ├── agents/           # Agent implementations
│   │   ├── base_agent.py
│   │   ├── chat_agent.py
│   │   ├── code_agent.py
│   │   └── analysis_agent.py
│   ├── cli/              # CLI interface
│   │   ├── main.py
│   │   ├── chat_interface.py
│   │   ├── tools_command.py
│   │   └── utils.py
│   ├── models/           # Data models
│   │   ├── configs.py
│   │   └── schemas.py
│   ├── monitoring/       # Observability
│   │   └── enhanced_monitoring.py
│   ├── tools/            # Tool system
│   │   ├── base.py      # Base classes
│   │   ├── registry.py   # Tool registry
│   │   ├── decorators.py # Tool decorators
│   │   ├── loader.py     # Dynamic loading
│   │   ├── validation.py # Security & validation
│   │   ├── documentation.py # Doc generation
│   │   └── builtin/      # Built-in tools
│   └── utils/            # Utilities
│       ├── dependencies.py
│       └── logfire_setup.py
├── examples/             # Example scripts
├── tests/               # Test suite
└── docs/                # Documentation
```

## Testing

Run the test suite:

```bash
# Run all tests
python run_tests.py all

# Run specific test suite
python run_tests.py agents

# Run with coverage
python run_tests.py coverage

# Quick test run
python run_tests.py quick
```

## Advanced Features

### Multi-Model Support

```python
# Use different AI providers
config = AgentConfig(
    name="MultiModelAgent",
    model="anthropic:claude-3-5-sonnet"  # or "google:gemini-2.0"
)
agent = ChatAgent(config)
```

### Tool System

```python
from src.tools import tool, tool_registry

# Create a custom tool
@tool(name="word_counter", description="Count words in text")
def count_words(text: str) -> dict:
    words = text.split()
    return {"word_count": len(words), "char_count": len(text)}

# Use tools in agents
from src.agents import ChatAgent

agent = ChatAgent(tools=[
    tool_registry.get("read_file"),
    tool_registry.get("word_counter")
])
```

### MCP Integration

```python
from src.mcp import create_mcp_server, create_mcp_client

# Expose tools as MCP server
server = create_mcp_server(
    categories=["file_system"],
    security_level="sandboxed"
)
await server.start()

# Connect to MCP server
client = create_mcp_client(
    server_command=["npx", "@modelcontextprotocol/server-name"]
)
await client.connect()

# Use remote tools
tools = await client.list_tools()
result = await client.call_tool("remote_tool", {"arg": "value"})
```

#### Claude Desktop Integration

Add to `claude_desktop_config.json`:

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

### Monitoring & Alerts

```python
from src.monitoring import monitor_operation, alert_manager

# Monitor operations
with monitor_operation("critical_task", agent_name="MyAgent"):
    result = await agent.process(data)

# Check alerts
alerts = alert_manager.check_alerts()
```

## Development

### Code Style

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Architecture

The system follows a modular architecture:

- **Agents**: Core AI functionality with PydanticAI
- **Models**: Pydantic models for type safety
- **CLI**: Rich terminal interface
- **Monitoring**: Comprehensive observability
- **Utils**: Shared utilities and helpers

## Performance

- Async-first design for optimal performance
- Connection pooling for API calls
- Intelligent caching mechanisms
- Retry logic with exponential backoff

## Security

- API keys stored securely in environment
- Input validation on all user inputs
- Safe code execution sandboxing
- Prompt injection protection

## Roadmap

- [x] Comprehensive tool system with sandboxing
- [ ] Memory persistence with vector databases
- [ ] Multi-agent coordination
- [ ] Advanced reasoning patterns (CoT, ReAct)
- [ ] Plugin system for custom agents
- [ ] Web UI dashboard
- [ ] Deployment templates

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: [docs/](docs/)
- Examples: [examples/](examples/)
- Issues: [GitHub Issues](https://github.com/yourusername/ajenitk-context/issues)

## Acknowledgments

Built with:
- [PydanticAI](https://ai.pydantic.dev/) - AI agent framework
- [Logfire](https://logfire.pydantic.dev/) - Observability platform
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Click](https://click.palletsprojects.com/) - CLI framework