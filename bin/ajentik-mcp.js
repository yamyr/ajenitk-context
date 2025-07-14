#!/usr/bin/env node

/**
 * Ajentik MCP CLI wrapper for Node.js
 * This provides a cross-platform CLI interface to the Python-based Ajentik MCP server
 */

const { spawn } = require('child_process');
const { program } = require('commander');
const path = require('path');
const fs = require('fs');
const which = require('which');
const chalk = require('chalk');
const ora = require('ora');

// Check if Python and pip are available
async function checkPythonDependencies() {
  try {
    await which('python3');
  } catch (error) {
    try {
      await which('python');
    } catch (error) {
      console.error(chalk.red('Error: Python is not installed or not in PATH'));
      console.error(chalk.yellow('Please install Python 3.9 or higher from https://python.org'));
      process.exit(1);
    }
  }
}

// Get Python executable
async function getPythonExecutable() {
  try {
    await which('python3');
    return 'python3';
  } catch (error) {
    return 'python';
  }
}

// Install Python dependencies if needed
async function ensurePythonDependencies() {
  const spinner = ora('Checking Python dependencies...').start();
  
  const pythonPath = await getPythonExecutable();
  const ajentikPath = path.join(__dirname, '..', 'src');
  
  // Check if ajentik module is available
  const checkProcess = spawn(pythonPath, ['-c', 'import ajentik'], {
    env: { ...process.env, PYTHONPATH: ajentikPath }
  });
  
  return new Promise((resolve, reject) => {
    checkProcess.on('close', async (code) => {
      if (code !== 0) {
        spinner.text = 'Installing Python dependencies...';
        
        // Install dependencies
        const pipProcess = spawn(pythonPath, ['-m', 'pip', 'install', '-e', path.join(__dirname, '..')], {
          stdio: 'inherit'
        });
        
        pipProcess.on('close', (code) => {
          if (code === 0) {
            spinner.succeed('Python dependencies installed');
            resolve();
          } else {
            spinner.fail('Failed to install Python dependencies');
            reject(new Error('Installation failed'));
          }
        });
      } else {
        spinner.succeed('Python dependencies ready');
        resolve();
      }
    });
  });
}

// Main CLI setup
program
  .name('ajentik-mcp')
  .description('Ajentik MCP (Model Context Protocol) server and client')
  .version(require('../package.json').version);

// MCP Server command
program
  .command('server')
  .description('Start Ajentik MCP server')
  .option('-t, --transport <type>', 'Transport type (stdio, sse)', 'stdio')
  .option('-p, --port <port>', 'Port for SSE transport', '3000')
  .option('-c, --categories <categories>', 'Tool categories to load (comma-separated)')
  .option('-s, --security <level>', 'Security level (unrestricted, safe, sandboxed, restricted)', 'safe')
  .option('--discover', 'Auto-discover tools from current directory')
  .action(async (options) => {
    await checkPythonDependencies();
    await ensurePythonDependencies();
    
    const pythonPath = await getPythonExecutable();
    const args = ['-m', 'ajentik', 'mcp', 'server'];
    
    if (options.transport) args.push('--transport', options.transport);
    if (options.port) args.push('--port', options.port);
    if (options.categories) args.push('--categories', options.categories);
    if (options.security) args.push('--security', options.security);
    if (options.discover) args.push('--discover');
    
    const serverProcess = spawn(pythonPath, args, {
      stdio: 'inherit',
      env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '..', 'src')
      }
    });
    
    serverProcess.on('error', (error) => {
      console.error(chalk.red(`Failed to start server: ${error.message}`));
      process.exit(1);
    });
    
    // Handle graceful shutdown
    process.on('SIGINT', () => {
      serverProcess.kill('SIGINT');
      process.exit(0);
    });
  });

// MCP Client connect command
program
  .command('connect <server>')
  .description('Connect to an MCP server')
  .option('-t, --timeout <seconds>', 'Connection timeout', '30')
  .action(async (server, options) => {
    await checkPythonDependencies();
    await ensurePythonDependencies();
    
    const pythonPath = await getPythonExecutable();
    const args = ['-m', 'ajentik', 'mcp', 'connect', server];
    
    if (options.timeout) args.push('--timeout', options.timeout);
    
    const clientProcess = spawn(pythonPath, args, {
      stdio: 'inherit',
      env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '..', 'src')
      }
    });
    
    clientProcess.on('error', (error) => {
      console.error(chalk.red(`Failed to connect: ${error.message}`));
      process.exit(1);
    });
  });

// List tools command
program
  .command('list-tools')
  .description('List available Ajentik tools')
  .option('-c, --categories <categories>', 'Filter by categories (comma-separated)')
  .action(async (options) => {
    await checkPythonDependencies();
    await ensurePythonDependencies();
    
    const pythonPath = await getPythonExecutable();
    const args = ['-m', 'ajentik', 'tools', 'list'];
    
    if (options.categories) args.push('--categories', options.categories);
    
    const listProcess = spawn(pythonPath, args, {
      stdio: 'inherit',
      env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '..', 'src')
      }
    });
  });

// Configure command
program
  .command('configure')
  .description('Configure Ajentik MCP for Claude Desktop')
  .action(async () => {
    const spinner = ora('Configuring Claude Desktop...').start();
    
    const configPath = path.join(
      process.env.HOME || process.env.USERPROFILE,
      'Library',
      'Application Support',
      'Claude',
      'claude_desktop_config.json'
    );
    
    try {
      let config = {};
      if (fs.existsSync(configPath)) {
        config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      }
      
      if (!config.mcpServers) {
        config.mcpServers = {};
      }
      
      // Add Ajentik MCP server configuration
      config.mcpServers['ajentik-mcp'] = {
        command: 'ajentik-mcp',
        args: ['server'],
        env: {}
      };
      
      // Create directory if it doesn't exist
      const configDir = path.dirname(configPath);
      if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
      }
      
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
      
      spinner.succeed('Claude Desktop configured successfully');
      console.log(chalk.green('\nAjentik MCP has been added to Claude Desktop configuration.'));
      console.log(chalk.yellow('Restart Claude Desktop to use Ajentik tools.'));
    } catch (error) {
      spinner.fail('Failed to configure Claude Desktop');
      console.error(chalk.red(error.message));
      process.exit(1);
    }
  });

// Info command
program
  .command('info')
  .description('Show Ajentik MCP information')
  .action(async () => {
    console.log(chalk.blue.bold('\nAjentik MCP - Model Context Protocol Implementation\n'));
    console.log(`Version: ${chalk.green(require('../package.json').version)}`);
    console.log(`Node: ${chalk.green(process.version)}`);
    
    const pythonPath = await getPythonExecutable();
    const pythonVersion = spawn(pythonPath, ['--version']);
    
    pythonVersion.stdout.on('data', (data) => {
      console.log(`Python: ${chalk.green(data.toString().trim())}`);
    });
    
    pythonVersion.stderr.on('data', (data) => {
      console.log(`Python: ${chalk.green(data.toString().trim())}`);
    });
    
    console.log('\nAvailable commands:');
    console.log('  ajentik-mcp server     - Start MCP server');
    console.log('  ajentik-mcp connect    - Connect to MCP server');
    console.log('  ajentik-mcp list-tools - List available tools');
    console.log('  ajentik-mcp configure  - Configure Claude Desktop');
    console.log('  ajentik-mcp info       - Show this information');
    
    console.log('\nFor more information, visit:');
    console.log(chalk.blue('https://github.com/yourusername/ajentik-context'));
  });

program.parse(process.argv);