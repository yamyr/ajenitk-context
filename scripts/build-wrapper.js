#!/usr/bin/env node

/**
 * Build script to prepare the package for npm publishing
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('Building Ajentik MCP wrapper...');

// Create dist directory
const distDir = path.join(__dirname, '..', 'dist');
if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// Create index.js for programmatic usage
const indexContent = `/**
 * Ajentik MCP - Programmatic API
 */

const { spawn } = require('child_process');
const path = require('path');

class AjentikMCP {
  constructor(options = {}) {
    this.options = {
      transport: 'stdio',
      port: 3000,
      security: 'safe',
      categories: null,
      ...options
    };
  }

  async startServer() {
    const args = ['-m', 'ajentik', 'mcp', 'server'];
    
    if (this.options.transport) args.push('--transport', this.options.transport);
    if (this.options.port) args.push('--port', this.options.port.toString());
    if (this.options.security) args.push('--security', this.options.security);
    if (this.options.categories) args.push('--categories', this.options.categories);
    
    this.serverProcess = spawn('python3', args, {
      stdio: this.options.transport === 'stdio' ? 'inherit' : 'pipe',
      env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '..', 'src')
      }
    });
    
    return new Promise((resolve, reject) => {
      this.serverProcess.on('spawn', () => resolve(this));
      this.serverProcess.on('error', reject);
    });
  }

  async stop() {
    if (this.serverProcess) {
      this.serverProcess.kill('SIGTERM');
      return new Promise((resolve) => {
        this.serverProcess.on('close', resolve);
      });
    }
  }

  async connectToServer(serverCommand) {
    const args = ['-m', 'ajentik', 'mcp', 'connect', serverCommand];
    
    return new Promise((resolve, reject) => {
      const clientProcess = spawn('python3', args, {
        stdio: 'pipe',
        env: {
          ...process.env,
          PYTHONPATH: path.join(__dirname, '..', 'src')
        }
      });
      
      let output = '';
      clientProcess.stdout.on('data', (data) => {
        output += data.toString();
      });
      
      clientProcess.on('close', (code) => {
        if (code === 0) {
          resolve(output);
        } else {
          reject(new Error(\`Connection failed with code \${code}\`));
        }
      });
    });
  }
}

module.exports = { AjentikMCP };
`;

fs.writeFileSync(path.join(distDir, 'index.js'), indexContent);

console.log('✓ Created dist/index.js');

// Copy Python files
console.log('✓ Python source files included');

// Create .npmignore
const npmignoreContent = `
# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.idea/
.vscode/
*.swp
*.swo

# Testing
.coverage
.pytest_cache/
htmlcov/

# OS
.DS_Store
Thumbs.db

# Project specific
*.log
*.pid
`;

fs.writeFileSync(path.join(__dirname, '..', '.npmignore'), npmignoreContent);
console.log('✓ Created .npmignore');

console.log('\nBuild complete!');