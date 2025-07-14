# Ajentik AI System Examples

This directory contains example scripts demonstrating various features and usage patterns of the Ajentik AI system.

## Examples Overview

### 1. Basic Chat (`01_basic_chat.py`)
- Simple conversation with ChatAgent
- Managing conversation history
- Handling responses and confidence scores
- Displaying suggested actions

**Run it:**
```bash
python examples/01_basic_chat.py
```

### 2. Code Generation (`02_code_generation.py`)
- Generating code in multiple languages
- Using different frameworks
- Handling dependencies and warnings
- Saving generated code to files

**Run it:**
```bash
python examples/02_code_generation.py
```

### 3. Code Analysis (`03_code_analysis.py`)
- Analyzing code for quality issues
- Security vulnerability detection
- Performance analysis
- Getting improvement suggestions
- Generating analysis reports

**Run it:**
```bash
python examples/03_code_analysis.py
```

### 4. Monitoring & Observability (`04_monitoring_example.py`)
- Real-time metrics collection
- Live dashboard visualization
- Alert management
- Metrics export (JSON/Markdown)
- System health monitoring

**Run it:**
```bash
python examples/04_monitoring_example.py
```

### 5. Advanced Features (`05_advanced_features.py`)
- Custom agent configuration
- Multiple model providers (OpenAI, Anthropic, Google)
- Conversation memory management
- Custom tool integration
- Error handling and retries
- Parallel agent processing

**Run it:**
```bash
python examples/05_advanced_features.py
```

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Create a `.env` file in the project root with your API keys:
   ```env
   # Required for most examples
   OPENAI_API_KEY=your-openai-key
   
   # Optional for multi-model examples
   ANTHROPIC_API_KEY=your-anthropic-key
   GOOGLE_API_KEY=your-google-key
   
   # Optional for monitoring
   LOGFIRE_WRITE_TOKEN=your-logfire-token
   ```

3. **Python version:**
   Requires Python 3.8 or higher

## Quick Start

1. Start with the basic chat example to understand the core functionality
2. Try code generation to see how agents can create code
3. Use code analysis to analyze existing code
4. Explore monitoring to understand system observability
5. Dive into advanced features for complex use cases

## Using the CLI

Instead of running scripts directly, you can also use the CLI:

```bash
# Interactive chat
ajentik chat --enhanced

# Generate code
ajentik code generate

# Analyze code
ajentik code analyze file.py

# View monitoring dashboard
ajentik monitor --live
```

## Common Patterns

### Async/Await Usage
All agents support both async and sync operations:

```python
# Async
response = await agent.chat(message, history)

# Sync
response = agent.chat_sync(message, history)
```

### Error Handling
Always wrap agent calls in try-except blocks:

```python
try:
    response = await agent.generate_code(request)
except Exception as e:
    print(f"Error: {e}")
```

### Monitoring Operations
Use context managers for monitoring:

```python
with monitor_operation("my_operation", agent_name="MyAgent"):
    result = await agent.run(prompt)
```

## Tips

1. **API Keys**: Make sure your API keys are properly configured
2. **Rate Limits**: Be mindful of API rate limits when running examples
3. **Costs**: Some examples use premium models that incur costs
4. **Logging**: Enable debug mode for detailed logging: `--debug`
5. **Monitoring**: Use Logfire dashboard for real-time insights

## Troubleshooting

### Import Errors
If you get import errors, make sure you're running from the project root:
```bash
cd /path/to/ajenitk-context
python examples/01_basic_chat.py
```

### API Errors
- Check your API keys in `.env`
- Verify your account has access to the requested models
- Check for rate limiting or quota issues

### Monitoring Issues
- Ensure Logfire is properly configured
- Check network connectivity
- Verify LOGFIRE_WRITE_TOKEN is set

## Contributing

Feel free to add more examples! Follow these guidelines:
- Use descriptive filenames (e.g., `06_feature_name.py`)
- Include comprehensive docstrings
- Add error handling
- Update this README with your example
- Test with multiple providers when applicable