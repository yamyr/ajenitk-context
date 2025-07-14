# Rename Summary: agentic → ajentik

This document summarizes all changes made to rename the project from "agentic" to "ajentik".

## Files Renamed

1. `agentic-coding.md` → `ajentik-coding.md`

## Command Changes

The CLI command has been changed from `agentic` to `ajentik`:

- `agentic chat` → `ajentik chat`
- `agentic code generate` → `ajentik code generate`
- `agentic code analyze` → `ajentik code analyze`
- `agentic monitor` → `ajentik monitor`
- `agentic config` → `ajentik config`
- `agentic version` → `ajentik version`

## Configuration Changes

### pyproject.toml
- CLI entry point: `ajentik = "src.cli.main:main"`
- Service name: `ajentik-ai`
- Description: "Ajentik AI system..."

### setup.py
- Console script: `ajentik=src.cli.main:main`
- Description: "Ajentik AI system..."

### Environment/Config Files
- Service name: `ajentik-ai` (in LogfireConfig)
- History file: `~/.ajentik_history`
- Cache directory: `~/.ajentik/`

## Documentation Updates

All documentation files have been updated:
- README.md
- INSTALL.md
- docs/GETTING_STARTED.md
- docs/CLI_GUIDE.md
- docs/API_REFERENCE.md
- docs/MONITORING.md
- docs/BEST_PRACTICES.md
- examples/README.md

## Source Code Updates

Updated module docstrings and system names in:
- src/__init__.py
- src/cli/main.py
- src/cli/utils.py
- src/agents/__init__.py
- src/models/configs.py
- src/models/schemas.py
- src/utils/__init__.py
- src/monitoring/enhanced_monitoring.py
- tests/__init__.py
- tests/test_cli.py

## Build and Test Scripts

Updated commands in:
- Makefile
- build.sh
- test_install.sh
- run_tests.py
- .github/workflows/ci.yml
- .github/workflows/publish.yml

## Project Documentation

Updated references in:
- planning.md
- tasks.md
- ajentik-coding.md (formerly agentic-coding.md)

## Installation

After these changes, the package will be installed and used as:

```bash
# Install
pip install ajenitk-context

# Use
ajentik chat --enhanced
ajentik code generate -l python
ajentik monitor --live
```

## Notes

- The package name remains `ajenitk-context` (unchanged)
- All "Agentic AI System" references are now "Ajentik AI System"
- The rename is complete and consistent across all files