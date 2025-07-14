# Leveraging MCP for Development Workflows

This guide shows how to use Ajentik's MCP capabilities to enhance your development workflow.

## Setting Up Your Development Environment

### 1. Install Ajentik with Development Tools

```bash
# Clone and install in development mode
git clone https://github.com/yourusername/ajentik-context.git
cd ajentik-context
pip install -e ".[dev]"

# Install additional development dependencies
pip install pytest-asyncio pytest-cov black ruff mypy
```

### 2. Configure Claude Desktop for Development

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ajentik-dev": {
      "command": "ajentik",
      "args": ["mcp", "server", "--discover", "--security", "safe"],
      "env": {
        "PYTHONPATH": "/path/to/your/project"
      }
    },
    "ajentik-project": {
      "command": "python",
      "args": ["/path/to/project/.ajentik/dev_server.py"],
      "env": {
        "PROJECT_ROOT": "/path/to/project"
      }
    }
  }
}
```

### 3. Create Project-Specific Tools

Create `.ajentik/dev_server.py`:

```python
#!/usr/bin/env python3
import os
import sys
import asyncio

# Add project root to Python path
project_root = os.environ.get('PROJECT_ROOT', os.getcwd())
sys.path.insert(0, project_root)

from ajentik.mcp import create_mcp_server
from ajentik.tools import tool
import subprocess
import json
from pathlib import Path

# Project-specific tools

@tool(name="project_setup", description="Setup development environment")
def setup_environment() -> dict:
    """Setup or verify development environment."""
    steps = []
    
    # Check Python version
    import sys
    steps.append({
        "step": "Python version",
        "status": "✓" if sys.version_info >= (3, 9) else "✗",
        "details": f"Python {sys.version}"
    })
    
    # Check virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    steps.append({
        "step": "Virtual environment",
        "status": "✓" if in_venv else "✗",
        "details": "Active" if in_venv else "Not activated"
    })
    
    # Install dependencies
    try:
        subprocess.run(["pip", "install", "-e", ".[dev]"], check=True)
        steps.append({
            "step": "Dependencies",
            "status": "✓",
            "details": "Installed"
        })
    except:
        steps.append({
            "step": "Dependencies",
            "status": "✗",
            "details": "Failed to install"
        })
    
    return {"steps": steps}

@tool(name="run_specific_test", description="Run specific test file or function")
def run_specific_test(test_path: str, verbose: bool = True) -> dict:
    """Run specific test with pytest."""
    cmd = ["pytest", test_path]
    if verbose:
        cmd.append("-v")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "errors": result.stderr,
        "command": " ".join(cmd)
    }

@tool(name="analyze_code_complexity", description="Analyze code complexity")
def analyze_complexity(path: str = "src/") -> dict:
    """Analyze code complexity metrics."""
    try:
        # Install radon if needed
        subprocess.run(["pip", "install", "radon"], capture_output=True)
        
        # Cyclomatic complexity
        cc_result = subprocess.run(
            ["radon", "cc", path, "-a", "-j"],
            capture_output=True,
            text=True
        )
        
        # Maintainability index
        mi_result = subprocess.run(
            ["radon", "mi", path, "-j"],
            capture_output=True,
            text=True
        )
        
        return {
            "cyclomatic_complexity": json.loads(cc_result.stdout) if cc_result.returncode == 0 else {},
            "maintainability_index": json.loads(mi_result.stdout) if mi_result.returncode == 0 else {}
        }
    except Exception as e:
        return {"error": str(e)}

@tool(name="generate_architecture_diagram", description="Generate project architecture diagram")
def generate_architecture() -> dict:
    """Generate architecture diagram using pyreverse."""
    try:
        subprocess.run(["pip", "install", "pylint"], capture_output=True)
        
        # Generate class diagram
        subprocess.run([
            "pyreverse",
            "-o", "png",
            "-p", "Ajentik",
            "src/"
        ])
        
        return {
            "generated": ["classes_Ajentik.png", "packages_Ajentik.png"],
            "location": os.getcwd()
        }
    except Exception as e:
        return {"error": str(e)}

@tool(name="profile_performance", description="Profile code performance")
def profile_code(script_path: str, output_format: str = "text") -> dict:
    """Profile Python script performance."""
    try:
        import cProfile
        import pstats
        from io import StringIO
        
        profiler = cProfile.Profile()
        
        # Run the script
        with open(script_path) as f:
            code = compile(f.read(), script_path, 'exec')
            profiler.enable()
            exec(code)
            profiler.disable()
        
        # Generate report
        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Top 20 functions
        
        return {
            "profile": stream.getvalue(),
            "total_calls": stats.total_calls,
            "total_time": stats.total_tt
        }
    except Exception as e:
        return {"error": str(e)}

# Start MCP server
async def main():
    server = create_mcp_server(
        name="ajentik-project-dev",
        version="1.0.0",
        tools=[
            setup_environment.tool,
            run_specific_test.tool,
            analyze_complexity.tool,
            generate_architecture.tool,
            profile_code.tool
        ]
    )
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## Development Workflows

### 1. Test-Driven Development (TDD) with MCP

Create `.ajentik/tdd_tools.py`:

```python
@tool(name="tdd_create_test", description="Create test file for new feature")
def create_test_file(feature_name: str, test_cases: list) -> dict:
    """Generate test file with test cases."""
    
    test_content = f'''import pytest
from ajentik.{feature_name} import *

class Test{feature_name.title()}:
    """Test cases for {feature_name}."""
'''
    
    for i, test_case in enumerate(test_cases):
        test_content += f'''
    def test_{test_case.replace(" ", "_").lower()}(self):
        """Test: {test_case}"""
        # TODO: Implement test
        assert False, "Test not implemented"
'''
    
    filename = f"tests/test_{feature_name}.py"
    Path(filename).write_text(test_content)
    
    return {
        "created": filename,
        "test_cases": len(test_cases)
    }

@tool(name="tdd_implement", description="Generate implementation stub")
def implement_feature(feature_name: str, test_file: str) -> dict:
    """Generate implementation based on tests."""
    
    # Parse test file to understand requirements
    with open(test_file) as f:
        test_content = f.read()
    
    # Extract test function names
    import re
    test_functions = re.findall(r'def (test_\w+)', test_content)
    
    # Generate implementation stub
    impl_content = f'''"""Implementation for {feature_name}."""

class {feature_name.title()}:
    """Main class for {feature_name}."""
    
    def __init__(self):
        """Initialize {feature_name}."""
        pass
'''
    
    # Add methods based on test names
    for test_func in test_functions:
        method_name = test_func.replace("test_", "")
        impl_content += f'''
    def {method_name}(self):
        """{method_name.replace("_", " ").title()}."""
        raise NotImplementedError("TODO: Implement {method_name}")
'''
    
    filename = f"src/{feature_name}.py"
    Path(filename).parent.mkdir(exist_ok=True)
    Path(filename).write_text(impl_content)
    
    return {
        "created": filename,
        "methods": len(test_functions)
    }

@tool(name="tdd_watch", description="Watch tests and run on change")
async def watch_tests(test_pattern: str = "tests/") -> dict:
    """Watch for test changes and run automatically."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class TestRunner(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith('.py'):
                    print(f"Running tests for {event.src_path}")
                    subprocess.run(["pytest", event.src_path, "-v"])
        
        observer = Observer()
        observer.schedule(TestRunner(), test_pattern, recursive=True)
        observer.start()
        
        return {"status": "Watching for changes..."}
    except ImportError:
        return {"error": "Install watchdog: pip install watchdog"}
```

### 2. Code Review Workflow

```python
@tool(name="review_pr", description="Review pull request changes")
def review_pull_request(pr_number: int) -> dict:
    """Analyze PR changes and provide review."""
    
    # Get PR diff
    diff = subprocess.run(
        ["gh", "pr", "diff", str(pr_number)],
        capture_output=True,
        text=True
    )
    
    if diff.returncode != 0:
        return {"error": "Failed to fetch PR"}
    
    # Analyze changes
    analysis = {
        "files_changed": len(diff.stdout.split("diff --git")),
        "additions": diff.stdout.count("\n+"),
        "deletions": diff.stdout.count("\n-"),
        "suggestions": []
    }
    
    # Check for common issues
    if "TODO" in diff.stdout:
        analysis["suggestions"].append("Remove TODO comments before merging")
    
    if "print(" in diff.stdout and "tests/" not in diff.stdout:
        analysis["suggestions"].append("Remove debug print statements")
    
    if not any(test in diff.stdout for test in ["test_", "Test"]):
        analysis["suggestions"].append("Add tests for new functionality")
    
    return analysis

@tool(name="suggest_improvements", description="Suggest code improvements")
def suggest_improvements(file_path: str) -> dict:
    """Analyze code and suggest improvements."""
    
    with open(file_path) as f:
        content = f.read()
    
    suggestions = []
    
    # Check for code smells
    import ast
    try:
        tree = ast.parse(content)
        
        # Check function length
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.body) > 20:
                    suggestions.append(f"Function '{node.name}' is too long ({len(node.body)} lines)")
        
        # Check for duplicate code
        # ... additional analysis ...
        
    except SyntaxError as e:
        suggestions.append(f"Syntax error: {e}")
    
    return {"suggestions": suggestions}
```

### 3. Documentation Workflow

```python
@tool(name="generate_api_docs", description="Generate API documentation")
def generate_api_documentation(module_path: str) -> dict:
    """Generate API docs for a module."""
    
    import pydoc
    import importlib
    
    # Import module
    module_name = module_path.replace("/", ".").replace(".py", "")
    module = importlib.import_module(module_name)
    
    # Generate HTML documentation
    html_doc = pydoc.html.page(pydoc.describe(module), pydoc.html.document(module))
    
    # Save documentation
    output_path = f"docs/api/{module_name}.html"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(html_doc)
    
    # Generate Markdown documentation
    md_doc = f"# {module_name} API Documentation\n\n"
    
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) or inspect.isfunction(obj):
            md_doc += f"## {name}\n\n"
            md_doc += f"{inspect.getdoc(obj)}\n\n"
            
            if inspect.isclass(obj):
                for method_name, method in inspect.getmembers(obj):
                    if inspect.ismethod(method) or inspect.isfunction(method):
                        if not method_name.startswith("_"):
                            md_doc += f"### {method_name}\n\n"
                            md_doc += f"{inspect.getdoc(method)}\n\n"
    
    md_output = f"docs/api/{module_name}.md"
    Path(md_output).write_text(md_doc)
    
    return {
        "html": output_path,
        "markdown": md_output
    }

@tool(name="check_docstring_coverage", description="Check documentation coverage")
def check_docstring_coverage(path: str = "src/") -> dict:
    """Check which functions/classes lack docstrings."""
    
    missing_docs = []
    total_items = 0
    documented_items = 0
    
    for py_file in Path(path).rglob("*.py"):
        with open(py_file) as f:
            try:
                tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        total_items += 1
                        
                        # Check for docstring
                        has_docstring = (
                            node.body and
                            isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, ast.Str)
                        )
                        
                        if has_docstring:
                            documented_items += 1
                        else:
                            missing_docs.append(f"{py_file}:{node.name}")
                            
            except SyntaxError:
                pass
    
    coverage = (documented_items / total_items * 100) if total_items > 0 else 0
    
    return {
        "coverage": f"{coverage:.1f}%",
        "total": total_items,
        "documented": documented_items,
        "missing": missing_docs[:10]  # First 10
    }
```

### 4. Deployment Workflow

```python
@tool(name="prepare_release", description="Prepare for release")
def prepare_release(version: str) -> dict:
    """Prepare project for release."""
    
    steps = []
    
    # Update version
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text()
    content = re.sub(r'version = "[^"]*"', f'version = "{version}"', content)
    pyproject.write_text(content)
    steps.append("Updated version in pyproject.toml")
    
    # Update changelog
    changelog = Path("CHANGELOG.md")
    if changelog.exists():
        new_entry = f"\n## v{version} - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        changelog.write_text(new_entry + changelog.read_text())
        steps.append("Updated CHANGELOG.md")
    
    # Run tests
    test_result = subprocess.run(["pytest"], capture_output=True)
    if test_result.returncode == 0:
        steps.append("All tests passed")
    else:
        return {"error": "Tests failed", "steps": steps}
    
    # Build distribution
    subprocess.run(["python", "-m", "build"], capture_output=True)
    steps.append("Built distribution packages")
    
    return {
        "version": version,
        "steps": steps,
        "ready": True
    }

@tool(name="deploy_to_pypi", description="Deploy to PyPI")
def deploy_pypi(test: bool = True) -> dict:
    """Deploy package to PyPI."""
    
    repository = "testpypi" if test else "pypi"
    
    # Check distribution files
    dist_files = list(Path("dist").glob("*"))
    if not dist_files:
        return {"error": "No distribution files found"}
    
    # Upload
    result = subprocess.run(
        ["twine", "upload", "--repository", repository, "dist/*"],
        capture_output=True,
        text=True
    )
    
    return {
        "success": result.returncode == 0,
        "output": result.stdout,
        "errors": result.stderr,
        "repository": repository
    }
```

## Integration with IDEs

### VS Code Extension

Create `.vscode/settings.json`:

```json
{
  "ajentik.mcp.server": {
    "command": "ajentik mcp server",
    "args": ["--categories", "development"],
    "autoStart": true
  },
  "ajentik.tools.custom": [
    ".ajentik/dev_tools.py"
  ]
}
```

### JetBrains Plugin

```xml
<!-- .idea/ajentik.xml -->
<component name="AjentikSettings">
  <option name="mcpServerCommand" value="ajentik mcp server" />
  <option name="toolCategories">
    <list>
      <option value="development" />
      <option value="testing" />
    </list>
  </option>
</component>
```

## Continuous Integration

### GitHub Actions with MCP

```yaml
name: MCP-Enhanced CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

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
        pip install -e .[dev]
        pip install ajentik-context
    
    - name: Start Development MCP Server
      run: |
        python .ajentik/dev_server.py &
        echo $! > dev-server.pid
        sleep 5
    
    - name: Run MCP-Enhanced Tests
      run: |
        # Connect to dev server
        ajentik mcp connect "python .ajentik/dev_server.py" <<EOF
        call run_specific_test {"test_path": "tests/"}
        call analyze_code_complexity {"path": "src/"}
        call check_docstring_coverage {}
        EOF
    
    - name: Generate Reports
      run: |
        ajentik mcp connect "python .ajentik/dev_server.py" <<EOF
        call generate_api_docs {"module_path": "src/ajentik"}
        EOF
    
    - name: Upload Reports
      uses: actions/upload-artifact@v3
      with:
        name: mcp-reports
        path: |
          docs/api/
          classes_*.png
    
    - name: Stop MCP Server
      if: always()
      run: |
        kill $(cat dev-server.pid) || true
```

## Best Practices

1. **Tool Organization**
   - Keep development tools in `.ajentik/` directory
   - Use categories to organize tools
   - Version control your custom tools

2. **Security**
   - Use appropriate security levels
   - Don't expose sensitive tools publicly
   - Validate all inputs

3. **Performance**
   - Cache expensive operations
   - Use async tools for I/O operations
   - Monitor tool execution times

4. **Documentation**
   - Document all custom tools
   - Include examples in tool descriptions
   - Generate API docs automatically

5. **Testing**
   - Test your custom tools
   - Use MCP client for integration tests
   - Monitor tool reliability

## Conclusion

By leveraging MCP in your development workflow:

- **Automate** repetitive tasks
- **Standardize** development processes
- **Share** tools across team members
- **Integrate** with AI assistants
- **Monitor** code quality continuously

The combination of Ajentik's tool system and MCP protocol creates a powerful development environment that enhances productivity and code quality.