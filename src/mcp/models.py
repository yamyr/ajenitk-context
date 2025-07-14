"""MCP protocol models and types."""

from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field


class MCPError(Exception):
    """Base exception for MCP errors."""
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class JSONRPCMessage(BaseModel):
    """Base JSON-RPC message."""
    jsonrpc: Literal["2.0"] = "2.0"
    id: Optional[Union[str, int]] = None


class JSONRPCRequest(JSONRPCMessage):
    """JSON-RPC request message."""
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(JSONRPCMessage):
    """JSON-RPC response message."""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class JSONRPCNotification(BaseModel):
    """JSON-RPC notification (no id)."""
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPToolParameter(BaseModel):
    """MCP tool parameter definition."""
    name: str
    description: Optional[str] = None
    required: bool = True
    schema_: Dict[str, Any] = Field(alias="schema")


class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: Optional[str] = None
    inputSchema: Dict[str, Any]


class MCPResource(BaseModel):
    """MCP resource definition."""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class MCPResourceTemplate(BaseModel):
    """MCP resource template definition."""
    uriTemplate: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class MCPPrompt(BaseModel):
    """MCP prompt definition."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPServerCapabilities(BaseModel):
    """Server capabilities."""
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None


class MCPClientCapabilities(BaseModel):
    """Client capabilities."""
    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None
    experimental: Optional[Dict[str, Any]] = None


class InitializeRequest(BaseModel):
    """Initialize request parameters."""
    protocolVersion: str
    capabilities: MCPClientCapabilities
    clientInfo: Dict[str, Any]


class InitializeResponse(BaseModel):
    """Initialize response."""
    protocolVersion: str
    capabilities: MCPServerCapabilities
    serverInfo: Dict[str, Any]


class CallToolRequest(BaseModel):
    """Tool call request."""
    name: str
    arguments: Optional[Dict[str, Any]] = None


class CallToolResponse(BaseModel):
    """Tool call response."""
    content: List[Dict[str, Any]]
    isError: Optional[bool] = False


class ListToolsResponse(BaseModel):
    """List tools response."""
    tools: List[MCPTool]


class ListResourcesResponse(BaseModel):
    """List resources response."""
    resources: List[MCPResource]


class ListResourceTemplatesResponse(BaseModel):
    """List resource templates response."""
    resourceTemplates: List[MCPResourceTemplate]


class ListPromptsResponse(BaseModel):
    """List prompts response."""
    prompts: List[MCPPrompt]


class ReadResourceRequest(BaseModel):
    """Read resource request."""
    uri: str


class ReadResourceResponse(BaseModel):
    """Read resource response."""
    contents: List[Dict[str, Any]]


class GetPromptRequest(BaseModel):
    """Get prompt request."""
    name: str
    arguments: Optional[Dict[str, Any]] = None


class GetPromptResponse(BaseModel):
    """Get prompt response."""
    description: Optional[str] = None
    messages: List[Dict[str, Any]]


class CompletionRequest(BaseModel):
    """Completion request."""
    ref: Dict[str, Any]
    argument: Dict[str, Any]


class CompletionResponse(BaseModel):
    """Completion response."""
    completion: Dict[str, Any]


class LoggingLevel(str, Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SetLoggingLevelRequest(BaseModel):
    """Set logging level request."""
    level: LoggingLevel


# MCP Error codes
class ErrorCode:
    """Standard JSON-RPC and MCP error codes."""
    # JSON-RPC errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP specific errors
    RESOURCE_NOT_FOUND = -32001
    TOOL_NOT_FOUND = -32002
    PROMPT_NOT_FOUND = -32003
    INVALID_TOOL_RESULT = -32004
    UNAUTHORIZED = -32005