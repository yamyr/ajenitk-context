# Getting Started with Ajentik AI System

This guide will help you get up and running with the Ajentik AI system quickly.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- At least one AI provider API key (OpenAI, Anthropic, or Google)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ajenitk-context.git
cd ajenitk-context
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required: At least one AI provider key
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=...

# Optional: Monitoring
# LOGFIRE_WRITE_TOKEN=...
```

### 5. Install the CLI Tool

```bash
pip install -e .
```

This installs the `ajentik` command globally.

## First Steps

### 1. Test the Installation

```bash
ajentik version
```

You should see version information.

### 2. Configure Settings

```bash
ajentik config
```

This will help you set up your configuration file.

### 3. Try Interactive Chat

Start with the enhanced chat interface:

```bash
ajentik chat --enhanced
```

Try these commands in chat:
- `/help` - See available commands
- `/settings` - View current settings
- Type a message to chat with the AI
- Type `exit` to quit

### 4. Generate Your First Code

```bash
ajentik code generate -l python
```

Follow the prompts to generate code.

### 5. Analyze Some Code

Create a simple Python file:

```python
# test.py
def add(a, b):
    return a + b

print(add(1, 2))
```

Analyze it:

```bash
ajentik code analyze test.py
```

## Using the Python API

### Basic Chat Example

```python
import asyncio
from src.agents import ChatAgent
from src.models import ConversationHistory

async def main():
    # Create agent
    agent = ChatAgent()
    
    # Create conversation
    history = ConversationHistory(messages=[], session_id="demo")
    
    # Chat
    response = await agent.chat(
        "What is Python?",
        conversation_history=history
    )
    
    print(response.message)

# Run
asyncio.run(main())
```

### Synchronous Version

```python
from src.agents import ChatAgent
from src.models import ConversationHistory

# Create agent
agent = ChatAgent()
history = ConversationHistory(messages=[], session_id="demo")

# Chat synchronously
response = agent.chat_sync(
    "What is Python?",
    conversation_history=history
)

print(response.message)
```

## Common Tasks

### Switch AI Providers

In your `.env`:

```env
# Use Anthropic Claude
DEFAULT_MODEL=anthropic:claude-3-5-sonnet

# Use Google Gemini
DEFAULT_MODEL=google:gemini-2.0
```

### Enable Monitoring

1. Get a Logfire account at https://logfire.pydantic.dev
2. Add to `.env`:

```env
LOGFIRE_WRITE_TOKEN=your-token
LOGFIRE_PROJECT=your-project
```

3. View dashboard:

```bash
ajentik monitor --live
```

### Customize Agent Behavior

```python
from src.models import AgentConfig
from src.agents import ChatAgent

config = AgentConfig(
    name="CustomBot",
    temperature=0.3,  # More focused responses
    system_message="You are a helpful Python tutor."
)

agent = ChatAgent(config)
```

## Troubleshooting

### API Key Issues

If you get authentication errors:

1. Check your `.env` file has the correct keys
2. Ensure no extra spaces or quotes around keys
3. Verify your API key is active on the provider's dashboard

### Import Errors

If you can't import modules:

1. Ensure you're in the project directory
2. Check virtual environment is activated
3. Reinstall with: `pip install -e .`

### Rate Limiting

If you hit rate limits:

1. Add delays between requests
2. Use a different model tier
3. Implement caching for repeated queries

## Next Steps

- Explore [examples/](../examples/) for more code samples
- Read [CLI_GUIDE.md](CLI_GUIDE.md) for advanced CLI usage
- Check [API_REFERENCE.md](API_REFERENCE.md) for detailed API docs
- See [MONITORING.md](MONITORING.md) for observability features

## Getting Help

- Check existing [examples](../examples/README.md)
- Review test files for usage patterns
- Open an issue on GitHub for bugs
- Refer to provider docs for model-specific features