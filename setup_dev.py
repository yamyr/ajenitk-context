"""Setup script for Ajentik development environment."""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

# ANSI color codes
GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
BLUE = '\033[34m'
RESET = '\033[0m'


class DevelopmentSetup:
    """Setup development environment for Ajentik."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.venv_dir = self.root_dir / ".venv"
        self.errors: List[str] = []
    
    def print_header(self, message: str):
        """Print colored header."""
        print(f"\n{BLUE}{'=' * 60}{RESET}")
        print(f"{BLUE}{message.center(60)}{RESET}")
        print(f"{BLUE}{'=' * 60}{RESET}\n")
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"{GREEN}✓ {message}{RESET}")
    
    def print_warning(self, message: str):
        """Print warning message."""
        print(f"{YELLOW}⚠ {message}{RESET}")
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"{RED}✗ {message}{RESET}")
        self.errors.append(message)
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> bool:
        """Run a command and return success status."""
        try:
            subprocess.run(cmd, check=True, cwd=cwd or self.root_dir)
            return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Command failed: {' '.join(cmd)}")
            return False
    
    def check_python_version(self) -> bool:
        """Check if Python version is compatible."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            self.print_error(f"Python 3.9+ required, found {version.major}.{version.minor}")
            return False
        self.print_success(f"Python {version.major}.{version.minor} detected")
        return True
    
    def setup_virtual_environment(self) -> bool:
        """Create and activate virtual environment."""
        if self.venv_dir.exists():
            self.print_warning("Virtual environment already exists")
            return True
        
        self.print_header("Creating Virtual Environment")
        
        if not self.run_command([sys.executable, "-m", "venv", str(self.venv_dir)]):
            return False
        
        self.print_success("Virtual environment created")
        
        # Get activation command based on OS
        if sys.platform == "win32":
            activate_cmd = str(self.venv_dir / "Scripts" / "activate.bat")
        else:
            activate_cmd = f"source {self.venv_dir / 'bin' / 'activate'}"
        
        print(f"\nTo activate the virtual environment, run:")
        print(f"  {activate_cmd}")
        
        return True
    
    def install_dependencies(self) -> bool:
        """Install project dependencies."""
        self.print_header("Installing Dependencies")
        
        # Determine pip command
        if sys.platform == "win32":
            pip_cmd = str(self.venv_dir / "Scripts" / "pip")
        else:
            pip_cmd = str(self.venv_dir / "bin" / "pip")
        
        # Upgrade pip
        if not self.run_command([pip_cmd, "install", "--upgrade", "pip"]):
            return False
        self.print_success("Pip upgraded")
        
        # Install main dependencies
        if not self.run_command([pip_cmd, "install", "-e", "."]):
            return False
        self.print_success("Main dependencies installed")
        
        # Install development dependencies
        if not self.run_command([pip_cmd, "install", "-e", ".[dev]"]):
            self.print_warning("Development dependencies not installed")
        else:
            self.print_success("Development dependencies installed")
        
        return True
    
    def setup_pre_commit(self) -> bool:
        """Setup pre-commit hooks."""
        self.print_header("Setting Up Pre-commit Hooks")
        
        # Check if pre-commit is installed
        try:
            subprocess.run(["pre-commit", "--version"], 
                         capture_output=True, check=True)
        except:
            self.print_warning("pre-commit not installed, skipping")
            return True
        
        # Install pre-commit hooks
        if not self.run_command(["pre-commit", "install"]):
            self.print_warning("Failed to install pre-commit hooks")
            return True
        
        self.print_success("Pre-commit hooks installed")
        return True
    
    def create_directories(self) -> bool:
        """Create necessary directories."""
        self.print_header("Creating Project Directories")
        
        directories = [
            "logs",
            "data",
            "cache",
            ".ajentik",
            "examples",
            "docs/api",
        ]
        
        for dir_name in directories:
            dir_path = self.root_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            self.print_success(f"Created {dir_name}/")
        
        return True
    
    def create_env_file(self) -> bool:
        """Create .env file from template."""
        self.print_header("Creating Environment File")
        
        env_file = self.root_dir / ".env"
        env_example = self.root_dir / ".env.example"
        
        if env_file.exists():
            self.print_warning(".env file already exists")
            return True
        
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            self.print_success("Created .env from .env.example")
        else:
            # Create a basic .env file
            env_content = """# Ajentik Environment Configuration

# Environment
AJENTIK_ENVIRONMENT=development
AJENTIK_DEBUG=true

# Logging
AJENTIK_LOG_LEVEL=INFO
AJENTIK_LOG_FORMAT=text

# Tool System
AJENTIK_TOOLS_SECURITY_LEVEL=safe
AJENTIK_TOOLS_ENABLE_STATISTICS=true

# MCP Settings
AJENTIK_MCP_TIMEOUT=30
AJENTIK_MCP_PROTOCOL_VERSION=2024-11-05

# API Settings (optional)
# AJENTIK_API_HOST=127.0.0.1
# AJENTIK_API_PORT=8000
# AJENTIK_API_KEY=your-secret-key

# Database (optional)
# AJENTIK_DB_URL=sqlite:///ajentik.db
"""
            env_file.write_text(env_content)
            self.print_success("Created .env with defaults")
        
        print("\nPlease review and update .env with your settings")
        return True
    
    def run_tests(self) -> bool:
        """Run initial tests to verify setup."""
        self.print_header("Running Tests")
        
        # Determine pytest command
        if sys.platform == "win32":
            pytest_cmd = str(self.venv_dir / "Scripts" / "pytest")
        else:
            pytest_cmd = str(self.venv_dir / "bin" / "pytest")
        
        # Run tests
        if not self.run_command([pytest_cmd, "tests/", "-v", "--tb=short"]):
            self.print_warning("Some tests failed - this is expected for initial setup")
        else:
            self.print_success("All tests passed!")
        
        return True
    
    def print_next_steps(self):
        """Print next steps for development."""
        self.print_header("Setup Complete!")
        
        if self.errors:
            print(f"\n{RED}Setup completed with {len(self.errors)} errors:{RESET}")
            for error in self.errors:
                print(f"  - {error}")
        
        print("\n📚 Next Steps:")
        print("1. Activate your virtual environment")
        print("2. Review and update .env configuration")
        print("3. Run 'ajentik --help' to see available commands")
        print("4. Start the MCP server: 'ajentik mcp server'")
        print("5. Check out examples/ directory for usage examples")
        
        print("\n🔧 Development Commands:")
        print("  pytest              - Run tests")
        print("  black .             - Format code")
        print("  ruff check .        - Lint code")
        print("  mypy src/           - Type check")
        
        print("\n📖 Documentation:")
        print("  - README.md for overview")
        print("  - DEVELOPMENT.md for development guide")
        print("  - MIGRATION_GUIDE.md for migration from old code")
    
    def run(self) -> bool:
        """Run the complete setup process."""
        print(f"{BLUE}Ajentik Development Environment Setup{RESET}")
        print(f"{BLUE}=====================================\n{RESET}")
        
        # Check Python version
        if not self.check_python_version():
            return False
        
        # Setup steps
        steps = [
            self.setup_virtual_environment,
            self.install_dependencies,
            self.setup_pre_commit,
            self.create_directories,
            self.create_env_file,
            self.run_tests,
        ]
        
        for step in steps:
            if not step():
                if len(self.errors) > 3:  # Stop if too many errors
                    self.print_error("Too many errors, aborting setup")
                    return False
        
        self.print_next_steps()
        return len(self.errors) == 0


def main():
    """Main entry point."""
    setup = DevelopmentSetup()
    success = setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()