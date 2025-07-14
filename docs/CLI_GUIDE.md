# CLI Guide

The Ajentik AI system provides a powerful command-line interface with rich interactivity.

## Installation

```bash
pip install -e .
```

This installs the `ajentik` command globally.

## Global Options

```bash
ajentik [OPTIONS] COMMAND [ARGS]...

Options:
  --debug         Enable debug mode with verbose output
  --no-logfire    Disable Logfire monitoring
  --help          Show help message
```

## Commands

### `ajentik chat`

Interactive chat with AI agents.

```bash
ajentik chat [OPTIONS]

Options:
  --history              Load conversation history
  --personality TEXT     Set chat personality (default: helpful)
  --enhanced            Use enhanced chat interface (recommended)
  --help                Show help message
```

#### Basic Chat

```bash
ajentik chat
```

- Type messages to chat with AI
- Type `exit` or `quit` to end session
- Shows confidence scores in debug mode

#### Enhanced Chat Interface

```bash
ajentik chat --enhanced
```

Enhanced features:
- **Commands**: Type `/` to see special commands
  - `/help` - Show available commands
  - `/history [n]` - Show last n messages
  - `/save [file]` - Save conversation
  - `/load [file]` - Load conversation
  - `/clear` - Clear history
  - `/context <file>` - Add file to context
  - `/settings` - View/change settings
  - `/export [format]` - Export conversation
  - `/stats` - Show conversation statistics
  - `/mode [mode]` - Change chat mode

- **File Context**: Add files to provide context
- **Auto-save**: Conversations saved automatically
- **Rich Formatting**: Markdown rendering in terminal

### `ajentik code generate`

Generate code using AI.

```bash
ajentik code generate [OPTIONS]

Options:
  -l, --language TEXT    Programming language (default: python)
  -f, --framework TEXT   Framework to use (e.g., fastapi, react)
  -o, --output TEXT      Output file path
  --help                 Show help message
```

#### Examples

```bash
# Interactive code generation
ajentik code generate

# Generate Python code
ajentik code generate -l python

# Generate React component
ajentik code generate -l typescript -f react

# Save to file
ajentik code generate -o my_script.py
```

#### Interactive Process

1. Describe what you want to generate
2. Optionally add specific requirements
3. Review generated code
4. Save to file if desired

### `ajentik code analyze`

Analyze code for issues and improvements.

```bash
ajentik code analyze [FILE] [OPTIONS]

Options:
  -t, --types TEXT       Analysis types (multiple allowed)
                        Default: quality, security, performance
  --help                Show help message
```

#### Examples

```bash
# Analyze a file
ajentik code analyze script.py

# Interactive file selection
ajentik code analyze

# Specific analysis types
ajentik code analyze script.py -t security -t performance

# Analyze multiple aspects
ajentik code analyze app.py -t quality -t security -t maintainability
```

#### Analysis Types

- **quality**: Code quality and style issues
- **security**: Security vulnerabilities
- **performance**: Performance bottlenecks
- **maintainability**: Code maintainability issues
- **best-practices**: Best practice violations

#### Output

- Summary of findings
- Detailed issues with severity
- Line numbers for specific problems
- Improvement suggestions
- Overall score (0-10)
- Metrics (lines, complexity, etc.)

### `ajentik monitor`

View monitoring dashboard and metrics.

```bash
ajentik monitor [OPTIONS]

Options:
  --live                Show live updating dashboard
  --export [json|markdown]  Export metrics to file
  --alerts              Show active alerts only
  --help                Show help message
```

#### Examples

```bash
# Interactive monitoring menu
ajentik monitor

# Live dashboard (updates every 2 seconds)
ajentik monitor --live

# Export metrics to JSON
ajentik monitor --export json

# Export metrics report
ajentik monitor --export markdown

# Check for alerts
ajentik monitor --alerts
```

#### Dashboard Features

- **Agent Performance**: Request counts, success rates, response times
- **Tool Usage**: Which tools are used, execution times
- **System Health**: Overall health metrics
- **Token Usage**: LLM token consumption and costs
- **Active Alerts**: System warnings and errors

### `ajentik config`

Configure the ajentik system.

```bash
ajentik config
```

Features:
- Creates `.env` file if missing
- Copies from `.env.example` if available
- Opens editor for configuration
- Guides through setup process

### `ajentik version`

Show version information.

```bash
ajentik version
```

Displays:
- Ajentik AI System version
- PydanticAI version
- Python version

## Interactive Main Menu

Running `ajentik` without arguments shows an interactive menu:

```bash
ajentik
```

Menu options:
1. 💬 Chat - Interactive conversation
2. 🔧 Generate Code - Create new code
3. 🔍 Analyze Code - Review code
4. 📊 Monitor - View dashboard
5. ⚙️ Configure - Setup settings
6. ❌ Exit

## Advanced Usage

### Debug Mode

Enable detailed logging:

```bash
ajentik --debug chat
```

Shows:
- API calls and responses
- Token usage
- Confidence scores
- Timing information
- Error stack traces

### Disable Monitoring

Run without Logfire:

```bash
ajentik --no-logfire chat
```

### Pipe Input

```bash
# Analyze file from pipe
cat script.py | ajentik code analyze

# Generate code from description
echo "Create a fibonacci function" | ajentik code generate
```

### Script Integration

```python
#!/usr/bin/env python
import subprocess

# Run CLI command
result = subprocess.run(
    ["ajentik", "code", "generate", "-l", "python"],
    input="Create a hello world function",
    text=True,
    capture_output=True
)

print(result.stdout)
```

## Configuration Files

### Settings Locations

1. `.env` - Environment variables
2. `~/.ajentik/config.json` - User settings (if created)
3. Command-line arguments (override all)

### Environment Variables

```env
# AI Providers
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...

# Models
DEFAULT_MODEL=openai:gpt-4o
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=1000

# Monitoring
LOGFIRE_WRITE_TOKEN=...
LOGFIRE_PROJECT=...
ENABLE_MONITORING=true

# CLI
CLI_THEME=dark
CLI_EDITOR=vim
```

## Tips and Tricks

### 1. Quick Code Generation

```bash
# One-liner for simple functions
echo "factorial function" | ajentik code generate -l python
```

### 2. Batch Analysis

```bash
# Analyze multiple files
for file in *.py; do
    echo "Analyzing $file..."
    ajentik code analyze "$file" -t security
done
```

### 3. Custom Aliases

Add to your shell config:

```bash
# ~/.bashrc or ~/.zshrc
alias ac="ajentik chat --enhanced"
alias ag="ajentik code generate"
alias aa="ajentik code analyze"
alias am="ajentik monitor --live"
```

### 4. Integration with Git

```bash
# Analyze changed files
git diff --name-only | xargs -I {} ajentik code analyze {}
```

### 5. VS Code Integration

```json
// .vscode/tasks.json
{
    "tasks": [
        {
            "label": "Analyze Current File",
            "type": "shell",
            "command": "ajentik code analyze ${file}"
        }
    ]
}
```

## Troubleshooting

### Command Not Found

```bash
# Reinstall CLI
pip install -e .

# Check installation
which ajentik
```

### Slow Response

- Use `--no-logfire` to disable monitoring
- Check network connection
- Try a different model with `DEFAULT_MODEL`

### Authentication Errors

- Verify API keys in `.env`
- Check key permissions on provider dashboard
- Try `ajentik config` to reconfigure

### Unicode/Emoji Issues

- Set terminal encoding: `export LANG=en_US.UTF-8`
- Use `--no-emoji` flag (if implemented)
- Switch to a Unicode-capable terminal