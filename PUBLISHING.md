# Publishing and Distribution Guide

This guide covers how to publish Ajentik and leverage MCP for development workflows.

## Publishing to PyPI

### 1. Prepare for Release

```bash
# Update version in pyproject.toml
version = "0.1.0"  # → "0.2.0"

# Update changelog
echo "## v0.2.0 - $(date +%Y-%m-%d)" >> CHANGELOG.md
echo "- Added comprehensive tool system" >> CHANGELOG.md
echo "- Full MCP (Model Context Protocol) support" >> CHANGELOG.md
echo "- Enhanced CLI with rich interactivity" >> CHANGELOG.md

# Run tests
python run_tests.py all

# Check code quality
ruff check src/
black src/ tests/
mypy src/
```

### 2. Build Distribution

```bash
# Install build tools
pip install build twine

# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build wheel and source distribution
python -m build

# Check the distribution
twine check dist/*
```

### 3. Test with TestPyPI

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ ajentik-context

# Verify it works
ajentik --version
ajentik tools list
```

### 4. Publish to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Now anyone can install with:
pip install ajentik-context
```

## Publishing MCP Server

### 1. NPM Package (for Node.js ecosystem)

Create `mcp-ajentik/package.json`:

```json
{
  "name": "@ajentik/mcp-server",
  "version": "0.1.0",
  "description": "MCP server for Ajentik tools",
  "bin": {
    "ajentik-mcp": "./bin/ajentik-mcp.js"
  },
  "scripts": {
    "start": "ajentik mcp server"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0"
  },
  "keywords": ["mcp", "ai", "tools", "ajentik"],
  "license": "MIT"
}
```

Create wrapper `bin/ajentik-mcp.js`:

```javascript
#!/usr/bin/env node
const { spawn } = require('child_process');

const args = process.argv.slice(2);
const child = spawn('ajentik', ['mcp', 'server', ...args], {
  stdio: 'inherit'
});

child.on('exit', (code) => {
  process.exit(code);
});
```

Publish:

```bash
npm publish --access public
```

### 2. Docker Image

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Ajentik
RUN pip install ajentik-context

# Expose for SSE transport
EXPOSE 3000

# Default to stdio transport
CMD ["ajentik", "mcp", "server"]
```

Build and publish:

```bash
# Build image
docker build -t ajentik/mcp-server:latest .

# Test locally
docker run -it ajentik/mcp-server:latest

# Push to Docker Hub
docker push ajentik/mcp-server:latest
```

### 3. GitHub Release

```bash
# Tag the release
git tag -a v0.2.0 -m "Release v0.2.0 with MCP support"
git push origin v0.2.0

# Create GitHub release with:
# - Changelog
# - Installation instructions
# - MCP integration examples
```

## Leveraging MCP for Development

### 1. Enhanced Development Workflow

#### Local Development Assistant

Create `.ajentik/dev-tools.py`:

```python
from ajentik.tools import tool

@tool(name="run_tests", description="Run project tests")
def run_tests(subset: str = "all") -> dict:
    """Run test suite."""
    import subprocess
    result = subprocess.run(
        ["python", "run_tests.py", subset],
        capture_output=True,
        text=True
    )
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "errors": result.stderr
    }

@tool(name="check_code", description="Run code quality checks")
def check_code(path: str = "src/") -> dict:
    """Run linting and type checking."""
    import subprocess
    
    checks = {}
    
    # Ruff
    ruff = subprocess.run(["ruff", "check", path], capture_output=True)
    checks["ruff"] = ruff.returncode == 0
    
    # Black
    black = subprocess.run(["black", "--check", path], capture_output=True)
    checks["black"] = black.returncode == 0
    
    # Mypy
    mypy = subprocess.run(["mypy", path], capture_output=True)
    checks["mypy"] = mypy.returncode == 0
    
    return checks

@tool(name="git_status", description="Get git repository status")
def git_status() -> dict:
    """Get current git status."""
    import subprocess
    import json
    
    # Get status
    status = subprocess.run(
        ["git", "status", "--porcelain", "-b"],
        capture_output=True,
        text=True
    )
    
    # Get recent commits
    log = subprocess.run(
        ["git", "log", "--oneline", "-5"],
        capture_output=True,
        text=True
    )
    
    return {
        "branch": status.stdout.split('\n')[0],
        "changes": status.stdout.split('\n')[1:],
        "recent_commits": log.stdout.split('\n')
    }
```

Add to Claude Desktop:

```json
{
  "mcpServers": {
    "ajentik-dev": {
      "command": "ajentik",
      "args": ["mcp", "server", "--tools", "run_tests", "check_code", "git_status"],
      "env": {
        "PYTHONPATH": "/path/to/project"
      }
    }
  }
}
```

### 2. CI/CD Integration

#### GitHub Actions with MCP

`.github/workflows/mcp-ci.yml`:

```yaml
name: MCP-Enhanced CI

on: [push, pull_request]

jobs:
  test-with-mcp:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Ajentik
      run: |
        pip install -e .
        pip install pytest-asyncio
    
    - name: Start MCP Server
      run: |
        ajentik mcp server --security sandboxed &
        echo $! > mcp-server.pid
        sleep 5
    
    - name: Run MCP Tests
      run: |
        python -m pytest tests/test_mcp.py -v
    
    - name: Test MCP Client Connection
      run: |
        ajentik mcp connect "ajentik mcp server" --no-register
    
    - name: Stop MCP Server
      if: always()
      run: |
        kill $(cat mcp-server.pid) || true
```

### 3. Development Tools via MCP

#### Code Generation Assistant

```python
@tool(name="generate_tool", description="Generate a new tool from template")
def generate_tool(name: str, description: str, category: str = "custom") -> dict:
    """Generate tool boilerplate."""
    
    template = f'''from ajentik.tools import tool

@tool(
    name="{name}",
    description="{description}",
    category="{category}"
)
def {name.replace('-', '_')}(input: str) -> dict:
    """Generated tool: {description}"""
    # TODO: Implement tool logic
    
    return {{
        "status": "success",
        "input": input,
        "output": f"Processed: {{input}}"
    }}
'''
    
    filename = f"tools/{name}.py"
    Path("tools").mkdir(exist_ok=True)
    Path(filename).write_text(template)
    
    return {
        "created": filename,
        "content": template
    }

@tool(name="add_test", description="Generate test for a tool")
def add_test(tool_name: str) -> dict:
    """Generate test boilerplate for a tool."""
    
    template = f'''import pytest
from ajentik.tools import tool_registry

def test_{tool_name.replace('-', '_')}():
    """Test {tool_name} tool."""
    tool = tool_registry.get("{tool_name}")
    assert tool is not None
    
    # Test basic functionality
    result = tool(input="test")
    assert result.success
    assert result.data is not None
    
    # Add more specific tests here
'''
    
    filename = f"tests/test_{tool_name}.py"
    Path(filename).write_text(template)
    
    return {
        "created": filename,
        "content": template
    }
```

### 4. Multi-Agent Development

#### Create Development Agent Network

```python
from ajentik.agents import ChatAgent
from ajentik.mcp import create_mcp_client

async def create_dev_network():
    """Create a network of specialized development agents."""
    
    # Connect to various MCP servers
    code_reviewer = await create_mcp_client(
        server_command=["npx", "@code-reviewer/mcp-server"]
    )
    
    test_runner = await create_mcp_client(
        server_command=["ajentik", "mcp", "server", "--categories", "testing"]
    )
    
    doc_generator = await create_mcp_client(
        server_command=["npx", "@doc-gen/mcp-server"]
    )
    
    # Create specialized agents
    agents = {
        "reviewer": ChatAgent(
            name="Code Reviewer",
            tools=await code_reviewer.list_tools()
        ),
        "tester": ChatAgent(
            name="Test Runner",
            tools=await test_runner.list_tools()
        ),
        "documenter": ChatAgent(
            name="Doc Generator",
            tools=await doc_generator.list_tools()
        )
    }
    
    return agents
```

### 5. Marketplace Integration

#### Publish to MCP Registry

Create `mcp-manifest.json`:

```json
{
  "name": "ajentik-tools",
  "version": "0.2.0",
  "description": "Comprehensive AI tool system with 50+ built-in tools",
  "author": "Ajentik Team",
  "license": "MIT",
  "homepage": "https://github.com/ajentik/ajentik-context",
  "categories": ["file-system", "data-processing", "ai-tools"],
  "transports": ["stdio", "sse"],
  "installation": {
    "pip": "ajentik-context",
    "npm": "@ajentik/mcp-server",
    "docker": "ajentik/mcp-server"
  },
  "tools": {
    "count": 50,
    "categories": [
      "file_system",
      "data",
      "web",
      "ai",
      "development"
    ]
  },
  "examples": [
    {
      "name": "File Management",
      "command": "ajentik mcp server --categories file_system"
    },
    {
      "name": "Development Tools",
      "command": "ajentik mcp server --tools run_tests check_code"
    }
  ]
}
```

## Development Best Practices

### 1. Tool Development Workflow

```bash
# 1. Create new tool
ajentik tools generate my-tool

# 2. Test locally
ajentik tools run my-tool --params input="test"

# 3. Add to MCP server
ajentik mcp server --tools my-tool

# 4. Test via MCP
ajentik mcp connect "ajentik mcp server" --no-register
# Then: call my-tool {"input": "test"}

# 5. Generate documentation
ajentik tools docs --tools my-tool
```

### 2. Continuous Integration

```python
# ci_tools.py
@tool(name="ci_validate", description="Validate CI/CD pipeline")
async def validate_ci(pipeline_file: str = ".github/workflows/ci.yml") -> dict:
    """Validate CI configuration."""
    import yaml
    
    with open(pipeline_file) as f:
        config = yaml.safe_load(f)
    
    issues = []
    
    # Check for MCP integration
    if "mcp" not in str(config).lower():
        issues.append("Consider adding MCP server tests")
    
    # Check for tool tests
    if "test_tools" not in str(config):
        issues.append("Add tool system tests")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "jobs": list(config.get("jobs", {}).keys())
    }
```

### 3. Documentation Generation

```bash
# Generate comprehensive docs
ajentik tools docs --format markdown --format html
ajentik mcp docs > docs/MCP_REFERENCE.md

# Create interactive API docs
pip install mkdocs mkdocs-material
mkdocs new .
echo "# Ajentik Documentation" > docs/index.md
mkdocs serve
```

## Monetization Strategies

### 1. Ajentik Pro (SaaS)

- Hosted MCP server with premium tools
- Advanced security and monitoring
- Team collaboration features
- API access and webhooks

### 2. Enterprise Edition

- On-premise deployment
- Custom tool development
- Priority support
- Compliance certifications

### 3. Tool Marketplace

- Sell premium tool packages
- Revenue sharing for tool developers
- Subscription model for tool access

### 4. Integration Services

- Custom MCP server setup
- Tool migration services
- Training and consulting

## Next Steps

1. **Immediate Actions**
   - [ ] Publish to PyPI
   - [ ] Create Docker images
   - [ ] Submit to MCP registry
   - [ ] Write announcement blog post

2. **Short Term (1-2 weeks)**
   - [ ] Create video tutorials
   - [ ] Build example integrations
   - [ ] Develop premium tools
   - [ ] Setup documentation site

3. **Medium Term (1-2 months)**
   - [ ] Launch Ajentik Pro
   - [ ] Build tool marketplace
   - [ ] Create VS Code extension
   - [ ] Develop mobile app

4. **Long Term (3-6 months)**
   - [ ] Enterprise features
   - [ ] Advanced AI capabilities
   - [ ] Multi-language SDKs
   - [ ] Global CDN for tools