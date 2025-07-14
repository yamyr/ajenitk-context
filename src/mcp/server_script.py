#!/usr/bin/env python3
"""Standalone MCP server script for Ajentik tools.

This script can be used directly with Claude Desktop or other MCP clients.
"""

import asyncio
import sys
import os
import argparse
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.mcp import create_mcp_server
from src.tools import tool_registry, tool_loader
from src.tools.validation import SecurityLevel


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(description='Ajentik MCP Server')
    parser.add_argument('--tools', nargs='+', help='Specific tools to expose')
    parser.add_argument('--categories', nargs='+', help='Tool categories to expose')
    parser.add_argument('--security', default='safe', 
                       choices=['unrestricted', 'safe', 'sandboxed', 'restricted'],
                       help='Security level')
    parser.add_argument('--discover', action='store_true', 
                       help='Discover and load all available tools')
    
    args = parser.parse_args()
    
    # Load tools if discovery is enabled
    if args.discover:
        logger.info("Discovering tools...")
        tool_loader.load_builtin_tools()
        # Could also load from other sources
    
    # Create server
    logger.info("Creating MCP server...")
    
    # Get specific tools if requested
    tools = None
    if args.tools:
        tools = []
        for tool_name in args.tools:
            tool = tool_registry.get(tool_name)
            if tool:
                tools.append(tool)
                logger.info(f"Added tool: {tool_name}")
            else:
                logger.warning(f"Tool not found: {tool_name}")
    
    # Create server with configuration
    server = create_mcp_server(
        name="ajentik-mcp-server",
        version="1.0.0",
        tools=tools,
        categories=args.categories,
        security_level=SecurityLevel(args.security)
    )
    
    # Log available tools
    if tools:
        logger.info(f"Exposing {len(tools)} specific tools")
    elif args.categories:
        count = sum(len(tool_registry.list_tools(cat)) for cat in args.categories)
        logger.info(f"Exposing {count} tools from categories: {args.categories}")
    else:
        count = len(tool_registry.list_tools())
        logger.info(f"Exposing all {count} available tools")
    
    # Start server
    logger.info("Starting MCP server on stdio...")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())