# Publishing Ajentik MCP to NPM

This guide explains how to publish Ajentik MCP to npm and test it locally.

## Prerequisites

1. **Node.js and npm installed**
   ```bash
   node --version  # Should be 16.0.0 or higher
   npm --version   # Should be 7.0.0 or higher
   ```

2. **npm account** (create one at https://www.npmjs.com/signup)

3. **Python 3.9+ installed** (required by users who install the package)

## Local Testing Before Publishing

### 1. Build the Package

```bash
# Install Node dependencies
npm install

# Run the build script
npm run build
```

### 2. Test Locally with npm link

```bash
# In the ajentik-context directory
npm link

# Now you can use it globally
ajentik-mcp --version
ajentik-mcp server
ajentik-mcp info
```

### 3. Test in Another Project

```bash
# Create a test directory
mkdir test-ajentik-npm
cd test-ajentik-npm

# Link to your local package
npm link ajentik-mcp

# Test the CLI
ajentik-mcp server
```

### 4. Pack and Inspect

```bash
# Create a tarball to see what will be published
npm pack

# Inspect the contents
tar -tf ajentik-mcp-0.1.0.tgz
```

## Publishing to NPM

### 1. Login to npm

```bash
npm login
# Enter your username, password, and email
```

### 2. Update Version (if needed)

```bash
# Update version in package.json
npm version patch  # or minor, major
```

### 3. Publish to npm

```bash
# Dry run (see what would be published)
npm publish --dry-run

# Actually publish
npm publish
```

### 4. Verify Publication

```bash
# Check if it's on npm
npm info ajentik-mcp

# Install globally from npm
npm install -g ajentik-mcp

# Test it
ajentik-mcp --version
```

## Publishing a Beta/Preview Version

```bash
# Update version with beta tag
npm version 0.1.0-beta.1

# Publish with beta tag
npm publish --tag beta

# Users can install beta with
npm install -g ajentik-mcp@beta
```

## Automated Publishing with GitHub Actions

Add to `.github/workflows/npm-publish.yml`:

```yaml
name: Publish to NPM

on:
  release:
    types: [created]

jobs:
  publish-npm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://registry.npmjs.org'
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - run: npm ci
      
      - run: npm test
      
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{secrets.NPM_TOKEN}}
```

## What Gets Published

The npm package includes:
- `bin/ajentik-mcp.js` - CLI entry point
- `dist/index.js` - Programmatic API
- `src/` - Python source files
- `scripts/` - Build and install scripts
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Python package config

## Usage After Publishing

### Global CLI Installation

```bash
# Install globally
npm install -g ajentik-mcp

# Use the CLI
ajentik-mcp server
ajentik-mcp configure  # Configure Claude Desktop
ajentik-mcp list-tools
```

### Programmatic Usage

```javascript
// Install as dependency
// npm install ajentik-mcp

const { AjentikMCP } = require('ajentik-mcp');

async function main() {
  const server = new AjentikMCP({
    transport: 'stdio',
    security: 'safe'
  });
  
  await server.startServer();
  console.log('MCP server running...');
}

main();
```

### In package.json Scripts

```json
{
  "scripts": {
    "mcp-server": "ajentik-mcp server",
    "mcp-dev": "ajentik-mcp server --discover --security safe"
  }
}
```

## Troubleshooting

### Python Not Found

If users get "Python not found" error:
```bash
# Windows
# Install Python from python.org or Microsoft Store

# macOS
brew install python3

# Linux
sudo apt-get install python3 python3-pip
```

### Permission Errors

```bash
# If you get EACCES errors
npm install -g ajentik-mcp --unsafe-perm

# Or use a Node version manager like nvm
```

### Module Not Found

If Python modules aren't found:
```bash
# The postinstall script should handle this, but manually:
pip install ajentik-context
```

## Version Management

Follow semantic versioning:
- `npm version patch` - Bug fixes (0.1.0 → 0.1.1)
- `npm version minor` - New features (0.1.0 → 0.2.0)  
- `npm version major` - Breaking changes (0.1.0 → 1.0.0)

## Updating the Package

1. Make your changes
2. Update version: `npm version patch`
3. Publish: `npm publish`
4. Create git tag: `git push --tags`

## NPM Package Best Practices

1. **Always test locally first** with `npm link`
2. **Use .npmignore** to exclude unnecessary files
3. **Include clear installation instructions** in README
4. **Document Python requirements** prominently
5. **Use `engines` field** to specify Node version
6. **Test on multiple platforms** before publishing

## Next Steps

After publishing to npm:

1. Add npm badge to README:
   ```markdown
   [![npm version](https://badge.fury.io/js/ajentik-mcp.svg)](https://www.npmjs.com/package/ajentik-mcp)
   ```

2. Update documentation with npm installation:
   ```markdown
   ## Installation
   
   ### Via npm (recommended)
   ```bash
   npm install -g ajentik-mcp
   ```
   
   ### Via pip
   ```bash
   pip install ajentik-context
   ```
   ```

3. Create a demo video showing installation and usage

4. Announce on relevant forums and social media