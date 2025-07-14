# Ajentik Tools System

The Ajentik framework includes a powerful and extensible tool system that allows agents to interact with external systems, perform computations, and execute various operations in a controlled and safe manner.

## Overview

The tool system provides:

- **Tool Registry**: Centralized management of all available tools
- **Dynamic Loading**: Load tools from files, modules, or directories
- **Validation & Security**: Built-in safety checks and sandboxing
- **Documentation**: Auto-generated documentation in multiple formats
- **CLI Integration**: Manage and execute tools from the command line

## Quick Start

### Using Built-in Tools

```python
from ajentik.tools import tool_registry

# Get a built-in tool
read_tool = tool_registry.get("read_file")

# Execute the tool
result = read_tool(path="/path/to/file.txt")

if result.success:
    print(f"File contents: {result.data}")
else:
    print(f"Error: {result.error}")
```

### Creating Custom Tools

#### Using Decorators

```python
from ajentik.tools import tool, ToolResult

@tool(
    name="my_calculator",
    description="Perform basic calculations",
    category="math",
    is_safe=True
)
def calculate(expression: str) -> dict:
    """Evaluate a mathematical expression."""
    try:
        result = eval(expression)  # Note: Use safe evaluator in production
        return {"result": result}
    except Exception as e:
        raise ToolError(f"Calculation failed: {e}")
```

#### Using Classes

```python
from ajentik.tools import Tool, ToolParameter, ToolParameterType, ToolResult

class DataProcessorTool(Tool):
    @property
    def name(self) -> str:
        return "data_processor"
    
    @property
    def description(self) -> str:
        return "Process data with various transformations"
    
    @property
    def category(self) -> str:
        return "data"
    
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="data",
                type=ToolParameterType.ARRAY,
                description="Input data array",
                required=True
            ),
            ToolParameter(
                name="operation",
                type=ToolParameterType.STRING,
                description="Operation to perform",
                required=True,
                constraints={"enum": ["sum", "average", "filter"]}
            )
        ]
    
    def execute(self, data: list, operation: str) -> ToolResult:
        if operation == "sum":
            result = sum(data)
        elif operation == "average":
            result = sum(data) / len(data) if data else 0
        else:
            return ToolResult(
                success=False,
                error=f"Unknown operation: {operation}"
            )
        
        return ToolResult(
            success=True,
            data={"result": result, "operation": operation}
        )
```

## Built-in Tools

### File System Tools

- **read_file**: Read contents of a file
- **write_file**: Write content to a file
- **list_directory**: List directory contents
- **delete_file**: Delete a file or directory
- **create_directory**: Create a new directory
- **file_exists**: Check if a file exists
- **get_file_info**: Get detailed file information

### Example Usage

```python
# List files in a directory
list_tool = tool_registry.get("list_directory")
result = list_tool(path="/home/user/documents", recursive=True, pattern="*.pdf")

# Write to a file
write_tool = tool_registry.get("write_file")
result = write_tool(
    path="/tmp/output.txt",
    content="Hello, World!",
    create_dirs=True
)
```

## CLI Commands

The Ajentik CLI provides comprehensive tool management:

### List Available Tools

```bash
# List all tools
ajentik tools list

# List tools in a specific category
ajentik tools list --category file_system

# Search for tools
ajentik tools list --search "file"

# Show detailed information
ajentik tools list --detailed
```

### Execute Tools

```bash
# Run a tool with parameters
ajentik tools run read_file --params path=/etc/hosts

# Run with JSON output
ajentik tools run calculator --params expression="2+2" --json

# Skip confirmation prompts
ajentik tools run delete_file --params path=/tmp/test.txt --no-confirm
```

### Load Custom Tools

```bash
# Load from a Python file
ajentik tools load /path/to/my_tools.py

# Load from a directory
ajentik tools load /path/to/tools/ --recursive

# Load from a module
ajentik tools load mypackage.tools --type module

# Load from configuration file
ajentik tools load tools.yaml --type config
```

### Tool Discovery

```bash
# Discover all available tools
ajentik tools discover

# Discover only built-in tools
ajentik tools discover --builtin --no-search-paths
```

### Validate Tools

```bash
# Validate tool safety
ajentik tools validate my_tool

# Validate with different security levels
ajentik tools validate my_tool --level sandboxed
```

### Generate Documentation

```bash
# Generate documentation in multiple formats
ajentik tools docs --format markdown --format html

# Generate for specific category
ajentik tools docs --category file_system

# Specify output directory
ajentik tools docs --output ./docs/tools
```

## Tool Configuration

### Loading Tools from Config

Create a `tools.yaml` file:

```yaml
tools:
  - type: module
    path: myapp.tools
  
  - type: file
    path: /home/user/custom_tools.py
  
  - type: directory
    path: ./project_tools/
    recursive: true
```

Load with:

```bash
ajentik tools load tools.yaml
```

### Environment Variables

- `AJENTIK_TOOL_PATH`: Colon-separated paths to search for tools
- `AJENTIK_TOOL_SECURITY`: Default security level (unrestricted/safe/sandboxed/restricted)

## Security and Validation

### Security Levels

1. **UNRESTRICTED**: No security checks
2. **SAFE**: Basic safety checks (default)
3. **SANDBOXED**: Full sandboxing with resource limits
4. **RESTRICTED**: Maximum restrictions

### Validation Example

```python
from ajentik.tools import ToolValidator, SecurityLevel

validator = ToolValidator(SecurityLevel.SANDBOXED)

# Add allowed paths for file operations
validator.add_allowed_path("/tmp")
validator.add_allowed_path("/home/user/safe_dir")

# Validate a tool
results = validator.validate_tool(my_tool)
if results["valid"]:
    print("Tool is safe to use")
else:
    print(f"Validation errors: {results['errors']}")
```

### Sandboxed Execution

```python
from ajentik.tools import ToolSandbox

sandbox = ToolSandbox()

# Set resource limits
sandbox.set_resource_limit("max_memory", 50 * 1024 * 1024)  # 50MB
sandbox.set_resource_limit("max_cpu_time", 10)  # 10 seconds

# Execute tool in sandbox
result = sandbox.execute_sandboxed(my_tool, param1="value1")
```

## Advanced Features

### Async Tools

```python
from ajentik.tools import async_tool
import aiohttp

@async_tool(
    name="web_fetcher",
    description="Fetch content from URLs",
    category="web"
)
async def fetch_url(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

### Tool Composition

```python
from ajentik.tools import CompositeTool

class DataPipelineTool(CompositeTool):
    def __init__(self):
        super().__init__([
            ReadFileTool(),
            DataProcessorTool(),
            WriteFileTool()
        ])
    
    @property
    def name(self) -> str:
        return "data_pipeline"
    
    def execute(self, input_file: str, output_file: str) -> ToolResult:
        # Read data
        read_result = self.execute_tool("read_file", path=input_file)
        if not read_result.success:
            return read_result
        
        # Process data
        process_result = self.execute_tool(
            "data_processor",
            data=read_result.data,
            operation="average"
        )
        
        # Write results
        return self.execute_tool(
            "write_file",
            path=output_file,
            content=str(process_result.data)
        )
```

### Custom Parameter Types

```python
from ajentik.tools import parameter

@tool()
@parameter("config", ToolParameterType.OBJECT, "Configuration object", 
          constraints={"properties": {"timeout": {"type": "number"}}})
@parameter("urls", ToolParameterType.ARRAY, "List of URLs to process",
          constraints={"items": {"type": "string", "format": "uri"}})
def batch_processor(config: dict, urls: list) -> dict:
    # Process URLs with config
    return {"processed": len(urls)}
```

## Tool Development Best Practices

1. **Always validate inputs**: Check parameters before processing
2. **Return structured results**: Use ToolResult for consistency
3. **Handle errors gracefully**: Catch exceptions and return error results
4. **Document parameters**: Provide clear descriptions
5. **Set appropriate safety flags**: Mark tools that modify state
6. **Use type hints**: Help with parameter extraction
7. **Test thoroughly**: Write unit tests for your tools

## Integration with Agents

Tools can be used by agents for enhanced capabilities:

```python
from ajentik.agents import ChatAgent
from ajentik.tools import tool_registry

# Create agent with tools
agent = ChatAgent(
    tools=[
        tool_registry.get("read_file"),
        tool_registry.get("web_fetcher"),
        tool_registry.get("calculator")
    ]
)

# Agent can now use tools in responses
response = agent.chat("Calculate the sum of numbers in data.txt")
```

## Monitoring and Metrics

Tool usage is automatically tracked:

```python
from ajentik.monitoring import metrics_collector

# Get tool metrics
stats = metrics_collector.tool_metrics
for tool_name, metrics in stats.items():
    print(f"{tool_name}: {metrics['usage_count']} uses, "
          f"{metrics['success_count']} successes")
```

## Troubleshooting

### Common Issues

1. **Tool not found**: Ensure tool is registered or loaded
2. **Parameter validation fails**: Check parameter types and requirements
3. **Security validation fails**: Review security level and tool implementation
4. **Import errors**: Ensure all dependencies are installed

### Debug Mode

Run with debug flag for detailed information:

```bash
ajentik --debug tools run my_tool --params key=value
```

## Examples

See the `examples/` directory for complete examples:

- `example_tool.py`: Various tool implementation patterns
- `custom_tools/`: Directory of custom tools
- `tool_config.yaml`: Configuration file example

## API Reference

For detailed API documentation, generate the docs:

```bash
ajentik tools docs --format html --output ./api-docs
```

Then open `./api-docs/tools.html` in your browser.