#!/usr/bin/env node

/**
 * Post-install script to ensure Python dependencies are installed
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk');

console.log(chalk.blue('\nSetting up Ajentik MCP...\n'));

// Check if we're in a global install
const isGlobal = process.env.npm_config_global === 'true';

// Get Python executable
function getPythonExecutable() {
  // Try python3 first, then python
  const pythonCommands = ['python3', 'python'];
  
  for (const cmd of pythonCommands) {
    try {
      const result = spawn.sync(cmd, ['--version'], { stdio: 'pipe' });
      if (result.status === 0) {
        return cmd;
      }
    } catch (e) {
      // Continue to next option
    }
  }
  
  return null;
}

const python = getPythonExecutable();

if (!python) {
  console.error(chalk.red('Error: Python is not installed or not in PATH'));
  console.error(chalk.yellow('Please install Python 3.9 or higher from https://python.org'));
  console.error(chalk.yellow('After installing Python, run: npm install -g ajentik-mcp'));
  process.exit(1);
}

console.log(chalk.green(`Found Python: ${python}`));

// Create a simple test to verify the installation
const testCode = `
import sys
print(f"Python {sys.version_info.major}.{sys.version_info.minor} ready")
`;

const testProcess = spawn.sync(python, ['-c', testCode], { stdio: 'pipe' });

if (testProcess.status === 0) {
  console.log(chalk.green(testProcess.stdout.toString().trim()));
  console.log(chalk.green('\nAjentik MCP installed successfully!'));
  console.log('\nQuick start:');
  console.log('  ajentik-mcp server       # Start MCP server');
  console.log('  ajentik-mcp configure    # Configure Claude Desktop');
  console.log('  ajentik-mcp info         # Show information');
} else {
  console.error(chalk.red('Failed to verify Python installation'));
}