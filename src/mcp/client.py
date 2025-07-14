"""MCP client implementation for connecting to MCP servers."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import uuid

from ..tools import tool_registry
from .models import (
    JSONRPCRequest, JSONRPCResponse, JSONRPCNotification,
    MCPError, ErrorCode,
    InitializeRequest, InitializeResponse,
    MCPClientCapabilities, CallToolRequest, CallToolResponse,
    ListToolsResponse, ReadResourceRequest, ReadResourceResponse,
    ListResourcesResponse, GetPromptRequest, GetPromptResponse,
    ListPromptsResponse
)
from .converters import mcp_to_tool, create_mcp_compatible_tool, mcp_response_to_tool_result
from .transport import Transport, StdioTransport


logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client for connecting to MCP servers."""
    
    def __init__(
        self,
        name: str = "ajentik-mcp-client",
        version: str = "1.0.0",
        transport: Optional[Transport] = None
    ):
        self.name = name
        self.version = version
        self.transport = transport or StdioTransport()
        
        # Client state
        self._initialized = False
        self._server_info: Optional[Dict[str, Any]] = None
        self._server_capabilities: Optional[Dict[str, Any]] = None
        
        # Request tracking
        self._pending_requests: Dict[Any, asyncio.Future] = {}
        self._next_id = 1
        
        # Notification handlers
        self._notification_handlers: Dict[str, List[Callable]] = {}
        
        # Running state
        self._running = False
        self._process_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to MCP server and initialize."""
        logger.info(f"Connecting MCP client: {self.name}")
        
        # Start transport
        if hasattr(self.transport, 'start'):
            await self.transport.start()
        
        self._running = True
        
        # Start message processing
        self._process_task = asyncio.create_task(self._process_messages())
        
        # Send initialize request
        await self._initialize()
    
    async def disconnect(self):
        """Disconnect from MCP server."""
        logger.info("Disconnecting MCP client")
        self._running = False
        
        # Cancel processing task
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        
        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        
        # Close transport
        await self.transport.close()
    
    async def _initialize(self):
        """Initialize connection with server."""
        # Build client capabilities
        capabilities = MCPClientCapabilities(
            roots={
                "listChanged": True
            },
            sampling={}
        )
        
        # Send initialize request
        response = await self._send_request(
            "initialize",
            InitializeRequest(
                protocolVersion="2024-11-05",
                capabilities=capabilities,
                clientInfo={
                    "name": self.name,
                    "version": self.version
                }
            ).dict()
        )
        
        # Parse response
        init_response = InitializeResponse(**response)
        self._server_info = init_response.serverInfo
        self._server_capabilities = init_response.capabilities.dict()
        
        # Send initialized notification
        await self._send_notification("initialized", {})
        
        self._initialized = True
        logger.info(f"Connected to server: {self._server_info}")
    
    async def _process_messages(self):
        """Process incoming messages from server."""
        while self._running:
            try:
                message = await self.transport.receive()
                if message is None:
                    break
                
                # Handle message
                await self._handle_message(message)
                
            except Exception as e:
                logger.error(f"Error processing messages: {e}")
                if not self._running:
                    break
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message."""
        try:
            # Check if response to a request
            if "id" in message and message["id"] in self._pending_requests:
                msg_id = message["id"]
                future = self._pending_requests.pop(msg_id)
                
                if "error" in message:
                    # Error response
                    error = message["error"]
                    future.set_exception(MCPError(
                        error.get("code", -1),
                        error.get("message", "Unknown error"),
                        error.get("data")
                    ))
                else:
                    # Success response
                    future.set_result(message.get("result"))
            
            # Check if notification
            elif "method" in message and "id" not in message:
                method = message["method"]
                params = message.get("params", {})
                
                # Call notification handlers
                if method in self._notification_handlers:
                    for handler in self._notification_handlers[method]:
                        try:
                            await handler(params)
                        except Exception as e:
                            logger.error(f"Notification handler error: {e}")
            
            else:
                logger.warning(f"Unhandled message: {message}")
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    async def _send_request(self, method: str, params: Any = None) -> Any:
        """Send a request and wait for response."""
        # Generate request ID
        msg_id = self._next_id
        self._next_id += 1
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[msg_id] = future
        
        # Send request
        request = JSONRPCRequest(
            id=msg_id,
            method=method,
            params=params
        )
        
        try:
            await self.transport.send(request.dict())
            
            # Wait for response
            return await future
            
        except Exception:
            # Clean up on error
            self._pending_requests.pop(msg_id, None)
            raise
    
    async def _send_notification(self, method: str, params: Any = None):
        """Send a notification (no response expected)."""
        notification = JSONRPCNotification(
            method=method,
            params=params
        )
        await self.transport.send(notification.dict())
    
    def on_notification(self, method: str, handler: Callable):
        """Register a notification handler."""
        if method not in self._notification_handlers:
            self._notification_handlers[method] = []
        self._notification_handlers[method].append(handler)
    
    # Tool methods
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from server."""
        if not self._initialized:
            raise RuntimeError("Client not initialized")
        
        response = await self._send_request("tools/list")
        list_response = ListToolsResponse(**response)
        
        return [tool.dict() for tool in list_response.tools]
    
    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> CallToolResponse:
        """Call a tool on the server."""
        if not self._initialized:
            raise RuntimeError("Client not initialized")
        
        request = CallToolRequest(
            name=name,
            arguments=arguments
        )
        
        response = await self._send_request("tools/call", request.dict())
        return CallToolResponse(**response)
    
    async def register_tools_locally(self, prefix: str = "mcp"):
        """Register MCP server tools in local registry."""
        tools = await self.list_tools()
        
        for tool_def in tools:
            # Create Ajentik-compatible tool
            tool_name = f"{prefix}_{tool_def['name']}" if prefix else tool_def['name']
            
            ajentik_tool = create_mcp_compatible_tool(
                name=tool_name,
                description=tool_def.get('description', ''),
                mcp_client=self
            )
            
            # Register in local registry
            tool_registry.register(ajentik_tool)
            logger.info(f"Registered MCP tool: {tool_name}")
    
    # Resource methods
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources from server."""
        if not self._initialized:
            raise RuntimeError("Client not initialized")
        
        if "resources" not in self._server_capabilities:
            return []
        
        response = await self._send_request("resources/list")
        list_response = ListResourcesResponse(**response)
        
        return [resource.dict() for resource in list_response.resources]
    
    async def read_resource(self, uri: str) -> ReadResourceResponse:
        """Read a resource from server."""
        if not self._initialized:
            raise RuntimeError("Client not initialized")
        
        if "resources" not in self._server_capabilities:
            raise RuntimeError("Server does not support resources")
        
        request = ReadResourceRequest(uri=uri)
        response = await self._send_request("resources/read", request.dict())
        
        return ReadResourceResponse(**response)
    
    # Prompt methods
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List available prompts from server."""
        if not self._initialized:
            raise RuntimeError("Client not initialized")
        
        if "prompts" not in self._server_capabilities:
            return []
        
        response = await self._send_request("prompts/list")
        list_response = ListPromptsResponse(**response)
        
        return [prompt.dict() for prompt in list_response.prompts]
    
    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> GetPromptResponse:
        """Get a prompt from server."""
        if not self._initialized:
            raise RuntimeError("Client not initialized")
        
        if "prompts" not in self._server_capabilities:
            raise RuntimeError("Server does not support prompts")
        
        request = GetPromptRequest(
            name=name,
            arguments=arguments
        )
        response = await self._send_request("prompts/get", request.dict())
        
        return GetPromptResponse(**response)
    
    # Utility methods
    
    async def ping(self) -> bool:
        """Ping the server."""
        try:
            await self._send_request("ping")
            return True
        except Exception:
            return False
    
    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information."""
        return self._server_info
    
    def get_server_capabilities(self) -> Optional[Dict[str, Any]]:
        """Get server capabilities."""
        return self._server_capabilities
    
    def supports_tools(self) -> bool:
        """Check if server supports tools."""
        return self._server_capabilities and "tools" in self._server_capabilities
    
    def supports_resources(self) -> bool:
        """Check if server supports resources."""
        return self._server_capabilities and "resources" in self._server_capabilities
    
    def supports_prompts(self) -> bool:
        """Check if server supports prompts."""
        return self._server_capabilities and "prompts" in self._server_capabilities


def create_mcp_client(
    server_command: Optional[List[str]] = None,
    server_url: Optional[str] = None,
    transport_type: str = "stdio",
    **kwargs
) -> MCPClient:
    """Create an MCP client with appropriate transport.
    
    Args:
        server_command: Command to launch server (for stdio)
        server_url: URL for server (for SSE/WebSocket)
        transport_type: Type of transport (stdio, sse, websocket)
        **kwargs: Additional client configuration
    
    Returns:
        Configured MCP client
    """
    # Create transport based on type
    if transport_type == "stdio":
        if server_command:
            # Launch server process
            import subprocess
            process = subprocess.Popen(
                server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Transport will use process stdio
        transport = StdioTransport()
        
    elif transport_type == "sse":
        if not server_url:
            raise ValueError("SSE transport requires server_url")
        from .transport import SSETransport
        transport = SSETransport(server_url)
        
    elif transport_type == "websocket":
        if not server_url:
            raise ValueError("WebSocket transport requires server_url")
        from .transport import WebSocketTransport
        transport = WebSocketTransport(server_url)
        
    else:
        raise ValueError(f"Unknown transport type: {transport_type}")
    
    # Create client
    client = MCPClient(transport=transport, **kwargs)
    
    return client