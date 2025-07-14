# Ajentik Coding Instructions for LLM

This document provides comprehensive instructions for LLMs (especially Claude) to perform ajentik coding tasks effectively in this project.

## Core Principles

### 1. Test-Driven Development (TDD)
- **Always write tests first** based on expected input/output pairs
- Explicitly state you're doing TDD to avoid mock implementations
- Run tests to confirm they fail before implementation
- Commit tests before implementing functionality
- Write code to pass tests without modifying the tests themselves
- Iterate until all tests pass

### 2. Extended Thinking Mode
Use these trigger words for complex problems:
- `think` - Basic extended thinking
- `think hard` - More computation time
- `think harder` - Even more computation time
- `ultrathink` - Maximum thinking budget

### 3. File Management
- Prefer editing existing files over creating new ones
- Use temporary files for testing when necessary
- Clean up temporary files after use
- Never create documentation files unless explicitly requested

## Repository Analysis Checklist

When starting work on a new repository, always perform these checks:

1. **Identify Project Type**
   - Run `ls -la` to see all files including hidden ones
   - Check for package.json (Node.js), requirements.txt (Python), Cargo.toml (Rust), etc.
   - Look for .gitignore to understand project structure
   - Check for build configuration files

2. **Understand Dependencies**
   - Read package manager files to understand available tools
   - Check for lock files (package-lock.json, yarn.lock, Pipfile.lock)
   - Verify installed dependencies before using them

3. **Locate Test Infrastructure**
   - Find test directories (test/, tests/, __tests__/, spec/)
   - Identify test runners (jest, pytest, mocha, etc.)
   - Check for test configuration files

4. **Check Code Quality Tools**
   - Look for .eslintrc, .prettierrc, .rubocop.yml, etc.
   - Find formatter configs (black, prettier, rustfmt)
   - Identify type checking configs (tsconfig.json, mypy.ini)

## Workflow Instructions

### Initial Repository Setup
1. Analyze repository structure using provided checklist
2. Identify technology stack and available tools
3. Check for existing documentation and conventions
4. Verify development environment requirements
5. Only then proceed with task implementation

### Task Planning and Tracking
1. Use TodoWrite tool to plan complex tasks
2. Break down large tasks into smaller, manageable steps
3. Mark todos as `in_progress` BEFORE starting work
4. Mark todos as `completed` IMMEDIATELY after finishing
5. Only have ONE task `in_progress` at a time

### Code Implementation Process
1. **Understand the codebase**
   - Use search tools extensively (Grep, Glob, Task)
   - Read existing code patterns and conventions
   - Check dependencies before using libraries

2. **Follow existing conventions**
   - Match code style in neighboring files
   - Use existing libraries and utilities
   - Follow naming conventions
   - Maintain consistent typing

3. **Verify and validate**
   - Run linters and formatters
   - Execute type checkers
   - Run test suites
   - Ensure builds succeed

### Git Workflow
1. **Never commit unless explicitly asked**
2. When committing:
   - Run `git status` to see changes
   - Run `git diff` to review modifications
   - Check `git log` for commit style
   - Use descriptive commit messages
   - Add co-author: `Co-Authored-By: Claude <noreply@anthropic.com>`

### Error Handling
- Tools must clearly report errors
- Handle edge cases gracefully
- Provide informative error messages
- Never ignore errors silently

## Project-Specific Guidelines

### Technology Stack
To be determined based on repository analysis. Common patterns:
- **Node.js/JavaScript**: Look for package.json, node_modules/
- **Python**: Look for requirements.txt, setup.py, pyproject.toml
- **Ruby**: Look for Gemfile, .ruby-version
- **Go**: Look for go.mod, go.sum
- **Rust**: Look for Cargo.toml, Cargo.lock
- **Java**: Look for pom.xml, build.gradle
- **C#/.NET**: Look for *.csproj, *.sln

### Code Style
- Use consistent indentation (spaces/tabs)
- Follow language-specific conventions
- No comments unless explicitly requested
- Keep code concise and readable

### Testing Requirements
- Unit tests for all functions
- Integration tests for workflows
- End-to-end tests for features
- Maintain test coverage above [X]%

### Build and Deploy
```bash
# Identify build system first, then use appropriate commands:

# Node.js/npm projects
npm install        # Install dependencies
npm run build      # Build the project
npm run test       # Run tests
npm run lint       # Run linter

# Python projects
pip install -r requirements.txt  # Install dependencies
python -m pytest                 # Run tests
python -m black .                # Format code
python -m mypy .                 # Type check

# Add other language-specific commands based on project type
```

## Language-Specific Guidelines

### JavaScript/TypeScript
- Check for `"type": "module"` in package.json for ESM
- Verify TypeScript is available before using types
- Check .nvmrc or .node-version for Node version
- Use npm scripts defined in package.json

### Python
- Check for virtual environment (.venv/, venv/)
- Identify Python version (check .python-version, runtime.txt)
- Use appropriate import style based on project
- Follow PEP 8 unless project specifies otherwise

### Other Languages
- [To be added based on project requirements]

## Best Practices

### 1. Concurrency
- Launch multiple independent tasks in parallel
- Use batch operations when possible
- Minimize sequential dependencies

### 2. Context Management
- Keep responses concise
- Focus on the specific task
- Avoid unnecessary explanations
- Reference code with `file_path:line_number`

### 3. Security
- Never expose secrets or keys
- Never commit sensitive information
- Follow security best practices
- Validate all inputs

### 4. Communication
- Be direct and concise
- Explain complex operations
- Ask for clarification when needed
- Report progress on long tasks

## Common Patterns

### Feature Implementation
1. Understand requirements
2. Search for related code
3. Write tests
4. Implement feature
5. Verify tests pass
6. Run linters/formatters
7. Update documentation if needed

### Bug Fixing
1. Reproduce the issue
2. Identify root cause
3. Write failing test
4. Fix the bug
5. Verify test passes
6. Check for regressions

### Refactoring
1. Understand current implementation
2. Ensure tests exist
3. Make incremental changes
4. Run tests after each change
5. Maintain backward compatibility

### Project Discovery
1. Run initial analysis commands:
   - `ls -la` for all files
   - `find . -type f -name "*.json" -o -name "*.yaml" -o -name "*.toml" | head -20`
   - `git ls-files | head -50` to see tracked files
2. Read configuration files to understand setup
3. Check for documentation beyond README
4. Identify entry points (main.js, app.py, index.html, etc.)
5. Look for example or demo directories

## Tool Usage

### Search Tools
- **Glob**: Find files by pattern
- **Grep**: Search file contents
- **Task**: Complex multi-step searches
- **LS**: List directory contents

### File Operations
- **Read**: View file contents
- **Edit**: Modify existing files
- **MultiEdit**: Multiple edits in one operation
- **Write**: Create new files (use sparingly)

### Development Tools
- **Bash**: Execute commands
- **WebSearch**: Find documentation
- **TodoWrite/TodoRead**: Task management

## Remember
- Do what's asked, nothing more or less
- Prefer editing over creating files
- Test everything before considering done
- Keep security in mind always
- Be concise in responses