# MCP Development Guide: Leveraging Ajentik for Maximum Productivity

## Table of Contents

1. [Quick Setup](#quick-setup)
2. [Development Workflows](#development-workflows)
3. [Integration Strategies](#integration-strategies)
4. [Business Opportunities](#business-opportunities)
5. [Advanced Patterns](#advanced-patterns)

## Quick Setup

### 1. Install and Configure

```bash
# Install Ajentik
pip install ajentik-context

# Or for development
git clone https://github.com/yourusername/ajentik-context.git
cd ajentik-context
pip install -e ".[dev]"
```

### 2. Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### 3. Verify Setup

```bash
# Start server manually to test
ajentik mcp server

# In another terminal, connect as client
ajentik mcp connect "ajentik mcp server"
```

## Development Workflows

### 1. AI-Assisted Development

#### Setup Development Environment

Create `.claude/project_tools.py`:

```python
from ajentik.tools import tool
import subprocess
import json

@tool(name="analyze_project", description="Analyze project structure and dependencies")
def analyze_project() -> dict:
    """Comprehensive project analysis."""
    analysis = {
        "structure": {},
        "dependencies": {},
        "issues": [],
        "suggestions": []
    }
    
    # Analyze file structure
    import os
    for root, dirs, files in os.walk(".", topdown=True):
        # Skip hidden and cache directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        level = root.replace(".", "").count(os.sep)
        indent = " " * 2 * level
        analysis["structure"][root] = {
            "files": len(files),
            "dirs": len(dirs),
            "python_files": len([f for f in files if f.endswith('.py')])
        }
    
    # Check dependencies
    if os.path.exists("requirements.txt"):
        with open("requirements.txt") as f:
            analysis["dependencies"]["requirements"] = f.read().splitlines()
    
    if os.path.exists("pyproject.toml"):
        import toml
        with open("pyproject.toml") as f:
            pyproject = toml.load(f)
            analysis["dependencies"]["pyproject"] = pyproject.get("project", {}).get("dependencies", [])
    
    # Check for common issues
    if not os.path.exists("tests/"):
        analysis["issues"].append("No tests directory found")
        analysis["suggestions"].append("Create tests/ directory and add unit tests")
    
    if not os.path.exists(".github/workflows/"):
        analysis["issues"].append("No GitHub Actions workflows")
        analysis["suggestions"].append("Add CI/CD workflows")
    
    return analysis

@tool(name="smart_refactor", description="Suggest refactoring improvements")
def suggest_refactoring(file_path: str) -> dict:
    """Analyze code and suggest improvements."""
    import ast
    import radon.complexity as radon_cc
    
    with open(file_path) as f:
        content = f.read()
    
    suggestions = []
    
    # Parse AST
    try:
        tree = ast.parse(content)
        
        # Check for long functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if len(node.body) > 20:
                    suggestions.append({
                        "type": "long_function",
                        "function": node.name,
                        "lines": len(node.body),
                        "suggestion": f"Consider breaking down {node.name} into smaller functions"
                    })
        
        # Check complexity
        cc_results = radon_cc.cc_visit(content)
        for result in cc_results:
            if result.complexity > 10:
                suggestions.append({
                    "type": "high_complexity",
                    "function": result.name,
                    "complexity": result.complexity,
                    "suggestion": f"Reduce complexity of {result.name} (current: {result.complexity})"
                })
        
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}
    
    return {"file": file_path, "suggestions": suggestions}

@tool(name="auto_document", description="Generate documentation for code")
def auto_document(file_path: str, style: str = "google") -> dict:
    """Generate docstrings for functions and classes."""
    import ast
    
    with open(file_path) as f:
        content = f.read()
        lines = content.splitlines()
    
    try:
        tree = ast.parse(content)
        insertions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Check if already has docstring
                has_docstring = (
                    node.body and
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))
                )
                
                if not has_docstring:
                    # Generate docstring
                    if isinstance(node, ast.FunctionDef):
                        docstring = generate_function_docstring(node, style)
                    else:
                        docstring = generate_class_docstring(node, style)
                    
                    # Calculate insertion point
                    insert_line = node.lineno
                    indent = len(lines[insert_line - 1]) - len(lines[insert_line - 1].lstrip())
                    
                    insertions.append({
                        "line": insert_line,
                        "indent": indent,
                        "docstring": docstring,
                        "name": node.name
                    })
        
        return {
            "file": file_path,
            "insertions": insertions,
            "count": len(insertions)
        }
        
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

def generate_function_docstring(node: ast.FunctionDef, style: str) -> str:
    """Generate docstring for a function."""
    args = []
    for arg in node.args.args:
        if arg.arg != 'self':
            args.append(arg.arg)
    
    if style == "google":
        docstring = f'"""Brief description of {node.name}.\n\n'
        if args:
            docstring += "Args:\n"
            for arg in args:
                docstring += f"    {arg}: Description of {arg}\n"
        docstring += "\nReturns:\n    Description of return value\n"
        docstring += '"""'
    else:  # numpy style
        docstring = f'"""Brief description of {node.name}.\n\n'
        if args:
            docstring += "Parameters\n----------\n"
            for arg in args:
                docstring += f"{arg} : type\n    Description of {arg}\n"
        docstring += "\nReturns\n-------\ntype\n    Description of return value\n"
        docstring += '"""'
    
    return docstring

def generate_class_docstring(node: ast.ClassDef, style: str) -> str:
    """Generate docstring for a class."""
    return f'"""Class {node.name} does something.\n\nMore detailed description.\n"""'
```

Add to Claude config:

```json
{
  "mcpServers": {
    "project-assistant": {
      "command": "python",
      "args": [".claude/project_tools.py"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

### 2. Automated Testing Workflow

```python
@tool(name="test_generator", description="Generate test cases from code")
def generate_tests(source_file: str) -> dict:
    """Generate unit tests for a source file."""
    import ast
    
    with open(source_file) as f:
        content = f.read()
    
    # Parse to find functions
    tree = ast.parse(content)
    test_cases = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            # Generate test case
            test_case = {
                "function": node.name,
                "test_name": f"test_{node.name}",
                "params": [arg.arg for arg in node.args.args if arg.arg != 'self'],
                "test_code": generate_test_code(node)
            }
            test_cases.append(test_case)
    
    # Generate test file content
    test_content = f"""import pytest
from {source_file.replace('.py', '').replace('/', '.')} import *

class Test{source_file.replace('.py', '').replace('/', '_').title()}:
"""
    
    for test in test_cases:
        test_content += f"\n{test['test_code']}\n"
    
    return {
        "source": source_file,
        "test_file": f"tests/test_{os.path.basename(source_file)}",
        "test_cases": test_cases,
        "content": test_content
    }

def generate_test_code(func_node: ast.FunctionDef) -> str:
    """Generate test code for a function."""
    params = [arg.arg for arg in func_node.args.args if arg.arg != 'self']
    
    test_code = f"""    def test_{func_node.name}(self):
        \"\"\"Test {func_node.name} function.\"\"\"
        # Arrange"""
    
    for param in params:
        test_code += f"\n        {param} = None  # TODO: Set test value"
    
    test_code += f"""
        
        # Act
        result = {func_node.name}({', '.join(params)})
        
        # Assert
        assert result is not None  # TODO: Add specific assertions"""
    
    return test_code

@tool(name="coverage_analyzer", description="Analyze test coverage")
def analyze_coverage(test_command: str = "pytest") -> dict:
    """Run tests with coverage analysis."""
    import subprocess
    
    # Install coverage if needed
    subprocess.run(["pip", "install", "coverage"], capture_output=True)
    
    # Run tests with coverage
    result = subprocess.run(
        ["coverage", "run", "-m", test_command],
        capture_output=True,
        text=True
    )
    
    # Generate coverage report
    report = subprocess.run(
        ["coverage", "report", "--format=json"],
        capture_output=True,
        text=True
    )
    
    # Parse results
    try:
        coverage_data = json.loads(report.stdout)
        
        # Find files with low coverage
        low_coverage = []
        for file, data in coverage_data.get("files", {}).items():
            if data["summary"]["percent_covered"] < 80:
                low_coverage.append({
                    "file": file,
                    "coverage": data["summary"]["percent_covered"],
                    "missing_lines": data["missing_lines"]
                })
        
        return {
            "total_coverage": coverage_data.get("totals", {}).get("percent_covered", 0),
            "files_analyzed": len(coverage_data.get("files", {})),
            "low_coverage_files": low_coverage,
            "test_passed": result.returncode == 0
        }
    except:
        return {
            "error": "Failed to parse coverage data",
            "stdout": report.stdout,
            "stderr": report.stderr
        }
```

### 3. Continuous Integration Enhancement

```python
@tool(name="ci_optimizer", description="Optimize CI/CD pipeline")
def optimize_ci_pipeline(workflow_file: str = ".github/workflows/ci.yml") -> dict:
    """Analyze and optimize CI pipeline."""
    import yaml
    
    with open(workflow_file) as f:
        workflow = yaml.safe_load(f)
    
    optimizations = []
    
    # Check for caching
    has_cache = False
    for job in workflow.get("jobs", {}).values():
        for step in job.get("steps", []):
            if "cache" in str(step).lower():
                has_cache = True
                break
    
    if not has_cache:
        optimizations.append({
            "type": "add_caching",
            "description": "Add dependency caching to speed up builds",
            "example": """
      - uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
"""
        })
    
    # Check for parallel jobs
    job_count = len(workflow.get("jobs", {}))
    if job_count > 1:
        # Check if jobs run in parallel
        has_dependencies = any(
            "needs" in job for job in workflow.get("jobs", {}).values()
        )
        if not has_dependencies:
            optimizations.append({
                "type": "parallel_execution",
                "description": "Jobs are already running in parallel",
                "status": "good"
            })
    
    # Check for matrix builds
    has_matrix = any(
        "strategy" in job and "matrix" in job["strategy"]
        for job in workflow.get("jobs", {}).values()
    )
    
    if not has_matrix and "test" in str(workflow).lower():
        optimizations.append({
            "type": "add_matrix",
            "description": "Use matrix builds to test multiple Python versions",
            "example": """
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]
"""
        })
    
    return {
        "workflow": workflow_file,
        "jobs": list(workflow.get("jobs", {}).keys()),
        "optimizations": optimizations,
        "estimated_speedup": f"{len(optimizations) * 15}%"
    }

@tool(name="deploy_assistant", description="Assist with deployment")
def deployment_checklist(environment: str = "production") -> dict:
    """Generate deployment checklist."""
    checklist = []
    
    # Version checks
    checklist.append({
        "task": "Update version number",
        "files": ["pyproject.toml", "src/__init__.py"],
        "status": "pending"
    })
    
    # Tests
    checklist.append({
        "task": "Run full test suite",
        "command": "pytest -v",
        "status": "pending"
    })
    
    # Documentation
    checklist.append({
        "task": "Update documentation",
        "files": ["README.md", "CHANGELOG.md", "docs/"],
        "status": "pending"
    })
    
    # Security
    checklist.append({
        "task": "Security scan",
        "command": "pip-audit",
        "status": "pending"
    })
    
    # Build
    checklist.append({
        "task": "Build distribution",
        "command": "python -m build",
        "status": "pending"
    })
    
    if environment == "production":
        checklist.extend([
            {
                "task": "Tag release",
                "command": "git tag -a v{version} -m 'Release v{version}'",
                "status": "pending"
            },
            {
                "task": "Create GitHub release",
                "url": "https://github.com/USER/REPO/releases/new",
                "status": "pending"
            }
        ])
    
    return {
        "environment": environment,
        "checklist": checklist,
        "total_tasks": len(checklist)
    }
```

## Integration Strategies

### 1. VS Code Extension

Create `ajentik-vscode/package.json`:

```json
{
  "name": "ajentik-tools",
  "displayName": "Ajentik Tools",
  "description": "Ajentik tool integration for VS Code",
  "version": "0.1.0",
  "engines": {
    "vscode": "^1.74.0"
  },
  "categories": ["Other"],
  "activationEvents": [
    "onStartupFinished"
  ],
  "main": "./extension.js",
  "contributes": {
    "commands": [
      {
        "command": "ajentik.runTool",
        "title": "Ajentik: Run Tool"
      },
      {
        "command": "ajentik.startServer",
        "title": "Ajentik: Start MCP Server"
      }
    ],
    "configuration": {
      "title": "Ajentik",
      "properties": {
        "ajentik.mcp.autoStart": {
          "type": "boolean",
          "default": true,
          "description": "Automatically start MCP server"
        },
        "ajentik.mcp.categories": {
          "type": "array",
          "default": ["development"],
          "description": "Tool categories to load"
        }
      }
    }
  }
}
```

### 2. Web Integration

```javascript
// ajentik-web-client.js
class AjentikWebClient {
  constructor(serverUrl) {
    this.serverUrl = serverUrl;
    this.eventSource = null;
  }

  async connect() {
    // SSE connection for real-time updates
    this.eventSource = new EventSource(`${this.serverUrl}/sse`);
    
    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    // Initialize connection
    const response = await fetch(`${this.serverUrl}/rpc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'ajentik-web' }
        },
        id: 1
      })
    });

    return response.json();
  }

  async listTools() {
    const response = await fetch(`${this.serverUrl}/rpc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/list',
        params: {},
        id: 2
      })
    });

    const result = await response.json();
    return result.result.tools;
  }

  async callTool(toolName, args) {
    const response = await fetch(`${this.serverUrl}/rpc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: args
        },
        id: Date.now()
      })
    });

    const result = await response.json();
    if (result.error) {
      throw new Error(result.error.message);
    }
    return result.result;
  }

  handleMessage(data) {
    // Handle server notifications
    console.log('Server message:', data);
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  }
}

// Usage example
const ajentik = new AjentikWebClient('http://localhost:3000');
await ajentik.connect();

const tools = await ajentik.listTools();
console.log('Available tools:', tools);

const result = await ajentik.callTool('analyze_code', {
  file_path: 'main.py'
});
console.log('Analysis result:', result);
```

### 3. Mobile App Integration

```swift
// AjentikMobile.swift
import Foundation

class AjentikMobileClient {
    private let serverURL: URL
    private var urlSession: URLSession
    
    init(serverURL: String) {
        self.serverURL = URL(string: serverURL)!
        self.urlSession = URLSession(configuration: .default)
    }
    
    func connect() async throws -> InitializeResponse {
        let request = JSONRPCRequest(
            method: "initialize",
            params: [
                "protocolVersion": "2024-11-05",
                "capabilities": [:],
                "clientInfo": ["name": "ajentik-ios"]
            ]
        )
        
        return try await sendRequest(request)
    }
    
    func listTools() async throws -> [Tool] {
        let request = JSONRPCRequest(method: "tools/list", params: [:])
        let response: ToolListResponse = try await sendRequest(request)
        return response.tools
    }
    
    func callTool(name: String, arguments: [String: Any]) async throws -> ToolResult {
        let request = JSONRPCRequest(
            method: "tools/call",
            params: [
                "name": name,
                "arguments": arguments
            ]
        )
        
        return try await sendRequest(request)
    }
    
    private func sendRequest<T: Decodable>(_ request: JSONRPCRequest) async throws -> T {
        var urlRequest = URLRequest(url: serverURL.appendingPathComponent("rpc"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONEncoder().encode(request)
        
        let (data, _) = try await urlSession.data(for: urlRequest)
        let response = try JSONDecoder().decode(JSONRPCResponse<T>.self, from: data)
        
        if let error = response.error {
            throw MCPError(message: error.message)
        }
        
        guard let result = response.result else {
            throw MCPError(message: "No result in response")
        }
        
        return result
    }
}
```

## Business Opportunities

### 1. Ajentik Pro (SaaS Platform)

```python
# ajentik_pro/subscription_tools.py
@tool(name="usage_analytics", description="Track tool usage for billing")
def track_usage(user_id: str, tool_name: str) -> dict:
    """Track tool usage for subscription billing."""
    # Implementation for usage tracking
    pass

@tool(name="premium_analyzer", description="Advanced code analysis")
def premium_code_analysis(repo_url: str) -> dict:
    """Premium feature: Full repository analysis."""
    # Advanced analysis implementation
    pass
```

### 2. Enterprise Features

```python
@tool(name="compliance_checker", description="Check regulatory compliance")
def check_compliance(standard: str = "SOC2") -> dict:
    """Enterprise feature: Compliance checking."""
    checks = {
        "SOC2": [
            "encryption_at_rest",
            "access_controls",
            "audit_logging",
            "data_retention"
        ],
        "HIPAA": [
            "phi_encryption",
            "access_logs",
            "data_integrity"
        ]
    }
    
    results = {}
    for check in checks.get(standard, []):
        # Perform compliance check
        results[check] = "pass"  # Simplified
    
    return {
        "standard": standard,
        "results": results,
        "compliant": all(r == "pass" for r in results.values())
    }
```

### 3. Marketplace Model

Create tool packages:

```python
# premium_tools/ai_tools.py
@tool(name="ai_code_review", description="AI-powered code review", premium=True)
def ai_code_review(file_path: str) -> dict:
    """Premium tool: AI code review."""
    # Use advanced AI models for code review
    pass

@tool(name="auto_refactor", description="Automatic refactoring", premium=True)
def auto_refactor(file_path: str, style: str = "pep8") -> dict:
    """Premium tool: Automatic code refactoring."""
    # Implement intelligent refactoring
    pass
```

### 4. Consulting Services

Offer:
- Custom tool development
- MCP server setup and optimization
- Integration with existing systems
- Training and workshops

## Advanced Patterns

### 1. Multi-Agent Collaboration

```python
async def multi_agent_development():
    """Coordinate multiple AI agents for development."""
    
    # Connect to different specialized servers
    code_agent = await create_mcp_client("ajentik mcp server --categories code")
    test_agent = await create_mcp_client("ajentik mcp server --categories testing")
    doc_agent = await create_mcp_client("ajentik mcp server --categories documentation")
    
    # Coordinate work
    # 1. Code agent generates implementation
    code_result = await code_agent.call_tool("generate_code", {
        "spec": "Create user authentication system"
    })
    
    # 2. Test agent creates tests
    test_result = await test_agent.call_tool("generate_tests", {
        "code": code_result.data
    })
    
    # 3. Doc agent creates documentation
    doc_result = await doc_agent.call_tool("generate_docs", {
        "code": code_result.data,
        "tests": test_result.data
    })
    
    return {
        "code": code_result,
        "tests": test_result,
        "docs": doc_result
    }
```

### 2. Self-Improving Tools

```python
@tool(name="tool_optimizer", description="Optimize tool performance")
def optimize_tool(tool_name: str) -> dict:
    """Analyze and optimize tool performance."""
    
    # Get tool execution history
    history = get_tool_execution_history(tool_name)
    
    # Analyze patterns
    patterns = {
        "avg_execution_time": sum(h["time"] for h in history) / len(history),
        "failure_rate": sum(1 for h in history if not h["success"]) / len(history),
        "common_errors": analyze_errors(history)
    }
    
    # Generate optimizations
    optimizations = []
    
    if patterns["avg_execution_time"] > 5.0:
        optimizations.append({
            "type": "performance",
            "suggestion": "Consider caching or async execution"
        })
    
    if patterns["failure_rate"] > 0.1:
        optimizations.append({
            "type": "reliability",
            "suggestion": "Add better error handling and retries"
        })
    
    return {
        "tool": tool_name,
        "patterns": patterns,
        "optimizations": optimizations
    }
```

### 3. Tool Composition

```python
from ajentik.tools import CompositeTool

class DevelopmentPipeline(CompositeTool):
    """Composite tool for full development pipeline."""
    
    def __init__(self):
        super().__init__([
            analyze_project.tool,
            generate_tests.tool,
            check_coverage.tool,
            optimize_ci_pipeline.tool
        ])
    
    @property
    def name(self) -> str:
        return "development_pipeline"
    
    async def execute(self, project_path: str) -> ToolResult:
        """Execute full development pipeline."""
        
        # 1. Analyze project
        analysis = await self.execute_tool("analyze_project")
        
        # 2. Generate missing tests
        for file in analysis.data["structure"]:
            if file.endswith(".py") and not file.startswith("test_"):
                await self.execute_tool("generate_tests", source_file=file)
        
        # 3. Check coverage
        coverage = await self.execute_tool("coverage_analyzer")
        
        # 4. Optimize CI if needed
        if coverage.data["total_coverage"] < 80:
            await self.execute_tool("optimize_ci_pipeline")
        
        return ToolResult(
            success=True,
            data={
                "analysis": analysis.data,
                "coverage": coverage.data,
                "status": "pipeline_complete"
            }
        )
```

## Conclusion

By leveraging Ajentik's MCP capabilities:

1. **Immediate Benefits**
   - Automate repetitive development tasks
   - Integrate AI assistance into your workflow
   - Standardize team practices
   - Improve code quality

2. **Business Opportunities**
   - Create and sell premium tools
   - Offer integration services
   - Build SaaS platforms
   - Develop industry-specific solutions

3. **Future Potential**
   - Multi-agent development teams
   - Self-improving codebases
   - Automated DevOps pipelines
   - AI-native development environments

Start small, experiment, and scale based on what works for your team!