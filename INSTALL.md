# Installation Guide

This guide covers different ways to install the Ajentik AI CLI system.

## Quick Install

### From PyPI (When Published)

```bash
pip install ajenitk-context
```

### From GitHub

```bash
pip install git+https://github.com/yourusername/ajenitk-context.git
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ajenitk-context.git
cd ajenitk-context

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Installation Methods

### 1. User Installation (Recommended)

For regular usage without modifying the code:

```bash
# Install from source
cd ajenitk-context
pip install .

# Or with all optional dependencies
pip install ".[dev]"
```

### 2. Developer Installation

For development and contribution:

```bash
# Install in editable mode
pip install -e .

# Install with development tools
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

### 3. System-wide Installation

For system-wide access (requires admin/sudo):

```bash
# On Linux/macOS
sudo pip install .

# On Windows (run as Administrator)
pip install .
```

### 4. Pipx Installation (Isolated Environment)

Using pipx for isolated CLI tools:

```bash
# Install pipx first
pip install pipx
pipx ensurepath

# Install ajenitk
pipx install .

# Or from git
pipx install git+https://github.com/yourusername/ajenitk-context.git
```

## Verifying Installation

After installation, verify the CLI is working:

```bash
# Check if command is available
which ajentik  # or `where ajentik` on Windows

# Show version
ajentik version

# Show help
ajentik --help

# Test basic functionality
ajentik config
```

## Configuration

### 1. Create Configuration File

```bash
# Copy example configuration
cp .env.example .env

# Or use the CLI
ajentik config
```

### 2. Set API Keys

Edit `.env` file:

```env
# Required: At least one AI provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional: Monitoring
LOGFIRE_WRITE_TOKEN=...
```

### 3. Test Configuration

```bash
# Test chat functionality
ajentik chat

# Test code generation
ajentik code generate -l python
```

## Troubleshooting

### Command Not Found

If `ajentik` command is not found:

1. **Check PATH**:
   ```bash
   echo $PATH
   # Ensure pip's bin directory is included
   ```

2. **Find installation location**:
   ```bash
   pip show -f ajenitk-context | grep "bin/ajentik"
   ```

3. **Add to PATH** (if needed):
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export PATH="$HOME/.local/bin:$PATH"
   ```

### Import Errors

If you get import errors:

1. **Check Python version**:
   ```bash
   python --version  # Should be 3.8+
   ```

2. **Verify installation**:
   ```bash
   pip list | grep ajenitk
   ```

3. **Reinstall**:
   ```bash
   pip uninstall ajenitk-context
   pip install .
   ```

### Permission Errors

If you get permission errors:

1. **Use virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install .
   ```

2. **Use user installation**:
   ```bash
   pip install --user .
   ```

3. **Use pipx** for isolated installation

## Updating

### From Git Repository

```bash
cd ajenitk-context
git pull origin main
pip install --upgrade .
```

### From PyPI (when published)

```bash
pip install --upgrade ajenitk-context
```

### Development Version

```bash
pip install --upgrade git+https://github.com/yourusername/ajenitk-context.git@main
```

## Uninstalling

### Standard Uninstall

```bash
pip uninstall ajenitk-context
```

### With pipx

```bash
pipx uninstall ajenitk-context
```

### Clean Uninstall

```bash
# Remove package
pip uninstall ajenitk-context

# Remove configuration (optional)
rm -rf ~/.ajentik
rm .env

# Remove cache (optional)
rm -rf ~/.cache/ajentik
```

## Platform-Specific Notes

### macOS

- Requires Python 3.8+ (install via Homebrew if needed)
- May need to install Xcode Command Line Tools

### Windows

- Use PowerShell or Command Prompt as Administrator for system-wide install
- Path separator is `;` instead of `:`
- Use `where` instead of `which` to find commands

### Linux

- Most distributions include Python 3.8+
- May need to install `python3-venv` package
- Use `python3` explicitly if `python` points to Python 2

## Docker Installation

For containerized deployment:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

# Set environment variables
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

ENTRYPOINT ["ajentik"]
```

Build and run:

```bash
docker build -t ajentik-cli .
docker run -it --rm ajentik-cli chat
```

## Next Steps

After installation:

1. Read [Getting Started](docs/GETTING_STARTED.md)
2. Configure your API keys
3. Try the examples in [examples/](examples/)
4. Explore the [CLI Guide](docs/CLI_GUIDE.md)