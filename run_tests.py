#!/usr/bin/env python3
"""
Test runner script for the agentic AI system.

This script provides an easy way to run different test suites
with various options.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """Run a command and return its exit code."""
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)
    result = subprocess.run(cmd)
    print()
    return result.returncode


def main():
    """Main test runner."""
    print("Ajentik AI System - Test Runner")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        print("\nAvailable test suites:")
        print("1. all     - Run all tests")
        print("2. unit    - Run unit tests only")
        print("3. agents  - Run agent tests")
        print("4. cli     - Run CLI tests")
        print("5. models  - Run model tests")
        print("6. monitor - Run monitoring tests")
        print("7. utils   - Run utility tests")
        print("8. coverage - Run with coverage report")
        print("9. quick   - Quick test run (no coverage)")
        
        choice = input("\nSelect test suite (1-9): ")
        test_type = {
            "1": "all",
            "2": "unit",
            "3": "agents",
            "4": "cli",
            "5": "models",
            "6": "monitor",
            "7": "utils",
            "8": "coverage",
            "9": "quick"
        }.get(choice, "all")
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    # Configure based on test type
    if test_type == "all":
        cmd = base_cmd + ["-v"]
    elif test_type == "unit":
        cmd = base_cmd + ["-v", "-m", "unit"]
    elif test_type == "agents":
        cmd = base_cmd + ["tests/test_agents.py", "-v"]
    elif test_type == "cli":
        cmd = base_cmd + ["tests/test_cli.py", "-v"]
    elif test_type == "models":
        cmd = base_cmd + ["tests/test_models.py", "-v"]
    elif test_type == "monitor":
        cmd = base_cmd + ["tests/test_monitoring.py", "-v"]
    elif test_type == "utils":
        cmd = base_cmd + ["tests/test_utils.py", "-v"]
    elif test_type == "coverage":
        cmd = base_cmd + ["--cov=src", "--cov-report=html", "--cov-report=term"]
    elif test_type == "quick":
        cmd = ["python", "-m", "pytest", "-x", "--tb=short", "--no-cov"]
    else:
        print(f"Unknown test type: {test_type}")
        return 1
    
    # Run the tests
    exit_code = run_command(cmd)
    
    if test_type == "coverage" and exit_code == 0:
        print("\nCoverage report generated in htmlcov/index.html")
        print("Open with: python -m http.server 8000 --directory htmlcov")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())