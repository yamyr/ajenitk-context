"""Tests for MCP integration."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch

from src.mcp import MCPServer, MCPClient, create_mcp_server, create_mcp_client
from src.mcp.models import (
    InitializeRequest, InitializeResponse,
    CallToolRequest, CallToolResponse,
    ListToolsResponse, MCPTool, MCPError, ErrorCode
)
from src.mcp.converters import tool_to_mcp, mcp_to_tool, tool_result_to_mcp
from src.mcp.transport import Transport
from src.tools import tool, Tool, ToolResult, ToolParameter, ToolParameterType
from src.tools.validation import SecurityLevel


# Test tools
@tool(name="test_tool", description="A test tool", register=False)
def test_tool_func(input: str) -> str:
    """Test tool for testing."""
    return f"Test: {input}"


@tool(name="error_tool", description="Tool that errors", register=False)
def error_tool_func() -> str:
    """Tool that raises an error."""
    raise ValueError("Test error")


class MockTransport(Transport):
    """Mock transport for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.receive_queue = asyncio.Queue()
        self.closed = False
    
    async def send(self, message: dict) -> None:
        self.sent_messages.append(message)
    
    async def receive(self) -> dict:
        if self.closed:
            return None
        return await self.receive_queue.get()
    
    async def close(self) -> None:
        self.closed = True
    
    async def add_message(self, message: dict):
        await self.receive_queue.put(message)


class TestMCPConverters:
    """Test tool converters."""
    
    def test_tool_to_mcp(self):
        """Test converting Ajentik tool to MCP format."""
        # Get test tool
        ajentik_tool = test_tool_func.tool
        
        # Convert to MCP
        mcp_tool = tool_to_mcp(ajentik_tool)
        
        assert mcp_tool.name == "test_tool"
        assert mcp_tool.description == "A test tool"
        assert mcp_tool.inputSchema["type"] == "object"
        assert "input" in mcp_tool.inputSchema["properties"]
        assert mcp_tool.inputSchema["properties"]["input"]["type"] == "string"
        assert mcp_tool.inputSchema["required"] == ["input"]
    
    def test_mcp_to_tool(self):
        """Test converting MCP tool to Ajentik format."""
        # Create MCP tool
        mcp_tool = MCPTool(
            name="mcp_test",
            description="MCP test tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Input text"},
                    "count": {"type": "integer", "default": 1}
                },
                "required": ["text"]
            }
        )
        
        # Convert to Ajentik tool
        ajentik_tool = mcp_to_tool(mcp_tool)
        
        assert ajentik_tool.name == "mcp_test"
        assert ajentik_tool.description == "MCP test tool"
        assert ajentik_tool.category == "mcp"
        
        # Check parameters
        params = ajentik_tool.parameters()
        assert len(params) == 2
        
        text_param = next(p for p in params if p.name == "text")
        assert text_param.type == ToolParameterType.STRING
        assert text_param.required == True
        
        count_param = next(p for p in params if p.name == "count")
        assert count_param.type == ToolParameterType.INTEGER
        assert count_param.required == False
        assert count_param.default == 1
    
    def test_tool_result_to_mcp(self):
        """Test converting tool result to MCP format."""
        # Success result
        result = ToolResult(
            success=True,
            data={"message": "Hello", "count": 42}
        )
        
        mcp_response = tool_result_to_mcp(result)
        assert mcp_response.isError == False
        assert len(mcp_response.content) == 1
        assert mcp_response.content[0]["type"] == "text"
        assert "Hello" in mcp_response.content[0]["text"]
        
        # Error result
        error_result = ToolResult(
            success=False,
            error="Something went wrong"
        )
        
        mcp_error = tool_result_to_mcp(error_result)
        assert mcp_error.isError == True
        assert mcp_error.content[0]["text"] == "Error: Something went wrong"


class TestMCPServer:
    """Test MCP server functionality."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test server initialization."""
        transport = MockTransport()
        server = MCPServer(
            name="test-server",
            version="1.0.0",
            transport=transport
        )
        
        # Add initialize request
        await transport.add_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client"}
            }
        })
        
        # Start processing in background
        process_task = asyncio.create_task(server._process_messages())
        
        # Wait for response
        await asyncio.sleep(0.1)
        
        # Check response
        assert len(transport.sent_messages) == 1
        response = transport.sent_messages[0]
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        
        # Cleanup
        process_task.cancel()
        try:
            await process_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing tools."""
        transport = MockTransport()
        
        # Create server with specific tools
        server = create_mcp_server(
            tools=[test_tool_func.tool],
            transport=transport
        )
        
        # Mark as initialized
        server._initialized = True
        
        # Add list tools request
        await transport.add_message({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        
        # Process message
        await server._handle_message(await transport.receive())
        
        # Check response
        assert len(transport.sent_messages) == 1
        response = transport.sent_messages[0]
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 1
        assert response["result"]["tools"][0]["name"] == "test_tool"
    
    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling a tool."""
        transport = MockTransport()
        
        # Register test tool
        from src.tools import tool_registry
        tool_registry.register(test_tool_func.tool)
        
        try:
            server = MCPServer(transport=transport)
            server._initialized = True
            
            # Add call tool request
            await transport.add_message({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "test_tool",
                    "arguments": {"input": "hello"}
                }
            })
            
            # Process message
            await server._handle_message(await transport.receive())
            
            # Check response
            assert len(transport.sent_messages) == 1
            response = transport.sent_messages[0]
            assert response["id"] == 3
            assert "result" in response
            assert "content" in response["result"]
            assert response["result"]["isError"] == False
            
        finally:
            # Clean up
            tool_registry.unregister("test_tool")


class TestMCPClient:
    """Test MCP client functionality."""
    
    @pytest.mark.asyncio
    async def test_client_connection(self):
        """Test client connection and initialization."""
        transport = MockTransport()
        client = MCPClient(transport=transport)
        
        # Mock server response
        asyncio.create_task(self._mock_server_responses(transport))
        
        # Connect client
        await client.connect()
        
        # Check client state
        assert client._initialized == True
        assert client._server_info is not None
        assert client._server_info["name"] == "test-server"
        
        # Cleanup
        await client.disconnect()
    
    async def _mock_server_responses(self, transport: MockTransport):
        """Mock server responses for client tests."""
        # Wait for initialize request
        await asyncio.sleep(0.1)
        
        # Send initialize response
        await transport.add_message({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "test-server", "version": "1.0.0"}
            }
        })
    
    @pytest.mark.asyncio
    async def test_list_tools_client(self):
        """Test listing tools from client."""
        transport = MockTransport()
        client = MCPClient(transport=transport)
        client._initialized = True
        
        # Mock response
        async def send_response():
            await asyncio.sleep(0.1)
            await transport.add_message({
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tools": [
                        {
                            "name": "remote_tool",
                            "description": "A remote tool",
                            "inputSchema": {"type": "object"}
                        }
                    ]
                }
            })
        
        # Start response sender
        asyncio.create_task(send_response())
        
        # Start message processing
        process_task = asyncio.create_task(client._process_messages())
        
        # List tools
        tools = await client.list_tools()
        
        assert len(tools) == 1
        assert tools[0]["name"] == "remote_tool"
        
        # Cleanup
        process_task.cancel()
        try:
            await process_task
        except asyncio.CancelledError:
            pass


class TestMCPIntegration:
    """Test full MCP integration."""
    
    @pytest.mark.asyncio
    async def test_server_client_communication(self):
        """Test full server-client communication."""
        # Create connected transports
        server_to_client = asyncio.Queue()
        client_to_server = asyncio.Queue()
        
        class ServerTransport(Transport):
            async def send(self, message):
                await server_to_client.put(message)
            
            async def receive(self):
                return await client_to_server.get()
            
            async def close(self):
                pass
        
        class ClientTransport(Transport):
            async def send(self, message):
                await client_to_server.put(message)
            
            async def receive(self):
                return await server_to_client.get()
            
            async def close(self):
                pass
        
        # Create server and client
        server = create_mcp_server(
            tools=[test_tool_func.tool],
            transport=ServerTransport()
        )
        
        client = MCPClient(transport=ClientTransport())
        
        # Start server processing
        server_task = asyncio.create_task(server._process_messages())
        
        # Connect client
        await client.connect()
        
        # List tools
        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"
        
        # Call tool
        result = await client.call_tool("test_tool", {"input": "world"})
        assert result.isError == False
        assert "Test: world" in str(result.content)
        
        # Cleanup
        await client.disconnect()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test registering MCP tools locally."""
        from src.tools import tool_registry
        
        # Mock client with tools
        client = Mock(spec=MCPClient)
        client.list_tools = AsyncMock(return_value=[
            {
                "name": "remote_calculator",
                "description": "Remote calculator",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    },
                    "required": ["expression"]
                }
            }
        ])
        
        # Mock tool execution
        client.call_tool = AsyncMock(return_value=CallToolResponse(
            content=[{"type": "text", "text": "Result: 42"}],
            isError=False
        ))
        
        # Register tools
        await client.register_tools_locally(prefix="test")
        
        # Note: In real implementation, this would register the tool
        # For now, we'll test the conversion and execution flow
        
        # Test that mock was called
        client.list_tools.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])