"""MCP server implementation for Ajentik tools."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from ..tools import tool_registry, Tool
from ..tools.validation import validate_tool_safety, SecurityLevel
from .models import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCNotification,
    MCPError, ErrorCode,
    InitializeRequest, InitializeResponse,
    MCPServerCapabilities, CallToolRequest, CallToolResponse,
    ListToolsResponse, MCPTool,
    SetLoggingLevelRequest, LoggingLevel
)
from .converters import tool_to_mcp, tool_result_to_mcp
from .transport import Transport, StdioTransport


logger = logging.getLogger(__name__)


class MCPServer:
    """MCP server that exposes Ajentik tools."""
    
    def __init__(
        self,
        name: str = "ajentik-mcp-server",
        version: str = "1.0.0",
        transport: Optional[Transport] = None,
        security_level: SecurityLevel = SecurityLevel.SAFE
    ):
        self.name = name
        self.version = version
        self.transport = transport or StdioTransport()
        self.security_level = security_level
        
        # Server state
        self._initialized = False
        self._client_info: Optional[Dict[str, Any]] = None
        self._capabilities = MCPServerCapabilities(
            tools={},
            logging={}
        )
        
        # Tool registry reference
        self._tool_registry = tool_registry
        
        # Request handlers
        self._handlers = {
            "initialize": self._handle_initialize,
            "initialized": self._handle_initialized,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            "logging/setLevel": self._handle_set_logging_level,
            "ping": self._handle_ping
        }
        
        # Running state
        self._running = False
        self._tasks: Set[asyncio.Task] = set()
    
    async def start(self):
        """Start the MCP server."""
        logger.info(f"Starting MCP server: {self.name} v{self.version}")
        
        # Start transport
        if hasattr(self.transport, 'start'):
            await self.transport.start()
        
        self._running = True
        
        # Start message processing
        await self._process_messages()
    
    async def stop(self):
        """Stop the MCP server."""
        logger.info("Stopping MCP server")
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close transport
        await self.transport.close()
    
    async def _process_messages(self):
        """Process incoming messages."""
        while self._running:
            try:
                message = await self.transport.receive()
                if message is None:
                    break
                
                # Handle message in background
                task = asyncio.create_task(self._handle_message(message))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
                
            except Exception as e:
                logger.error(f"Error processing messages: {e}")
                if not self._running:
                    break
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle a single message."""
        try:
            # Parse JSON-RPC request
            if "method" not in message:
                await self._send_error(
                    message.get("id"),
                    ErrorCode.INVALID_REQUEST,
                    "Missing method"
                )
                return
            
            method = message["method"]
            params = message.get("params", {})
            msg_id = message.get("id")
            
            # Check if notification (no id)
            is_notification = msg_id is None
            
            # Get handler
            handler = self._handlers.get(method)
            if not handler:
                if not is_notification:
                    await self._send_error(
                        msg_id,
                        ErrorCode.METHOD_NOT_FOUND,
                        f"Method not found: {method}"
                    )
                return
            
            # Execute handler
            try:
                result = await handler(params)
                
                # Send response if not notification
                if not is_notification:
                    await self._send_response(msg_id, result)
                    
            except MCPError as e:
                if not is_notification:
                    await self._send_error(msg_id, e.code, e.message, e.data)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                if not is_notification:
                    await self._send_error(
                        msg_id,
                        ErrorCode.INTERNAL_ERROR,
                        str(e)
                    )
                    
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    async def _send_response(self, msg_id: Any, result: Any):
        """Send a response message."""
        response = JSONRPCResponse(
            id=msg_id,
            result=result.dict() if hasattr(result, 'dict') else result
        )
        await self.transport.send(response.dict())
    
    async def _send_error(self, msg_id: Any, code: int, message: str, data: Any = None):
        """Send an error response."""
        response = JSONRPCResponse(
            id=msg_id,
            error={
                "code": code,
                "message": message,
                "data": data
            }
        )
        await self.transport.send(response.dict())
    
    async def _send_notification(self, method: str, params: Any = None):
        """Send a notification."""
        notification = JSONRPCNotification(
            method=method,
            params=params
        )
        await self.transport.send(notification.dict())
    
    # Request handlers
    
    async def _handle_initialize(self, params: Dict[str, Any]) -> InitializeResponse:
        """Handle initialize request."""
        request = InitializeRequest(**params)
        
        # Store client info
        self._client_info = request.clientInfo
        
        # Check protocol version
        if request.protocolVersion != "2024-11-05":
            raise MCPError(
                ErrorCode.INVALID_PARAMS,
                f"Unsupported protocol version: {request.protocolVersion}"
            )
        
        # Build capabilities
        self._capabilities = MCPServerCapabilities(
            tools={"listChanged": True},
            logging={}
        )
        
        # Mark as initialized
        self._initialized = True
        
        return InitializeResponse(
            protocolVersion="2024-11-05",
            capabilities=self._capabilities,
            serverInfo={
                "name": self.name,
                "version": self.version
            }
        )
    
    async def _handle_initialized(self, params: Dict[str, Any]) -> None:
        """Handle initialized notification."""
        logger.info("Client initialized")
        
        # Send initial tool list notification
        await self._send_notification("notifications/tools/listChanged")
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> ListToolsResponse:
        """Handle list tools request."""
        if not self._initialized:
            raise MCPError(
                ErrorCode.INVALID_REQUEST,
                "Server not initialized"
            )
        
        # Get all tools from registry
        tools = self._tool_registry.list_tools()
        
        # Filter by security level
        safe_tools = []
        for tool in tools:
            if validate_tool_safety(tool, self.security_level):
                safe_tools.append(tool)
        
        # Convert to MCP format
        mcp_tools = [tool_to_mcp(tool) for tool in safe_tools]
        
        return ListToolsResponse(tools=mcp_tools)
    
    async def _handle_call_tool(self, params: Dict[str, Any]) -> CallToolResponse:
        """Handle tool call request."""
        if not self._initialized:
            raise MCPError(
                ErrorCode.INVALID_REQUEST,
                "Server not initialized"
            )
        
        request = CallToolRequest(**params)
        
        # Get tool from registry
        tool = self._tool_registry.get(request.name)
        if not tool:
            raise MCPError(
                ErrorCode.TOOL_NOT_FOUND,
                f"Tool not found: {request.name}"
            )
        
        # Validate tool safety
        if not validate_tool_safety(tool, self.security_level):
            raise MCPError(
                ErrorCode.UNAUTHORIZED,
                f"Tool '{request.name}' does not meet security requirements"
            )
        
        # Execute tool
        try:
            # Log tool call
            logger.info(f"Calling tool: {request.name}")
            await self._send_notification(
                "notifications/message",
                {
                    "level": "info",
                    "logger": "tools",
                    "data": f"Executing tool: {request.name}"
                }
            )
            
            # Execute with provided arguments
            result = tool(**(request.arguments or {}))
            
            # Convert result to MCP format
            mcp_response = tool_result_to_mcp(result)
            
            # Log result
            if result.success:
                logger.info(f"Tool {request.name} completed successfully")
            else:
                logger.warning(f"Tool {request.name} failed: {result.error}")
            
            return mcp_response
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            raise MCPError(
                ErrorCode.INTERNAL_ERROR,
                f"Tool execution failed: {str(e)}"
            )
    
    async def _handle_set_logging_level(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set logging level request."""
        request = SetLoggingLevelRequest(**params)
        
        # Map MCP level to Python logging level
        level_map = {
            LoggingLevel.DEBUG: logging.DEBUG,
            LoggingLevel.INFO: logging.INFO,
            LoggingLevel.WARNING: logging.WARNING,
            LoggingLevel.ERROR: logging.ERROR
        }
        
        # Set logging level
        logger.setLevel(level_map[request.level])
        logging.getLogger("ajentik").setLevel(level_map[request.level])
        
        return {}
    
    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request."""
        return {}


def create_mcp_server(
    tools: Optional[List[Tool]] = None,
    categories: Optional[List[str]] = None,
    security_level: SecurityLevel = SecurityLevel.SAFE,
    transport: Optional[Transport] = None,
    **kwargs
) -> MCPServer:
    """Create and configure an MCP server.
    
    Args:
        tools: Specific tools to expose (None for all)
        categories: Tool categories to expose
        security_level: Security level for tool validation
        transport: Transport to use (defaults to stdio)
        **kwargs: Additional server configuration
    
    Returns:
        Configured MCP server
    """
    server = MCPServer(
        transport=transport,
        security_level=security_level,
        **kwargs
    )
    
    # Register specific tools if provided
    if tools:
        # Create a custom registry for this server
        from ..tools.registry import ToolRegistry
        custom_registry = ToolRegistry()
        
        for tool in tools:
            custom_registry.register(tool)
        
        server._tool_registry = custom_registry
    
    # Filter by categories if specified
    elif categories:
        # Create filtered registry
        from ..tools.registry import ToolRegistry
        filtered_registry = ToolRegistry()
        
        for category in categories:
            for tool in tool_registry.list_tools(category):
                filtered_registry.register(tool)
        
        server._tool_registry = filtered_registry
    
    return server