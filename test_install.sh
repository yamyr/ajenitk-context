#!/bin/bash
# Test installation script

set -e

echo "Testing ajenitk-context installation..."
echo "======================================"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Create virtual environment
echo "Creating virtual environment..."
cd $TEMP_DIR
python3 -m venv test_venv
source test_venv/bin/activate

# Install the package
echo "Installing ajenitk-context..."
cd $OLDPWD
pip install -e .

# Test imports
echo -e "\nTesting Python imports..."
python3 -c "
from src import ChatAgent, CodeAgent, AnalysisAgent
from src import AgentConfig, ConversationHistory
from src import monitor_operation, metrics_collector
print('✓ All imports successful')
"

# Test CLI commands
echo -e "\nTesting CLI commands..."
echo "1. Version check:"
ajentik version || echo "Failed to run version command"

echo -e "\n2. Help check:"
ajentik --help || echo "Failed to run help command"

echo -e "\n3. Subcommand check:"
ajentik chat --help || echo "Failed to run chat help"
ajentik code --help || echo "Failed to run code help"
ajentik monitor --help || echo "Failed to run monitor help"

# Check command location
echo -e "\nCommand location:"
which ajentik || echo "ajentik command not found in PATH"

# Cleanup
deactivate
cd /
rm -rf $TEMP_DIR

echo -e "\nInstallation test completed!"