"""Converters between Ajentik tools and MCP tools."""

from typing import Dict, Any, List, Optional
import json

from ..tools.base import Tool, ToolParameter, ToolParameterType, ToolResult
from ..tools.decorators import tool
from .models import MCPTool, CallToolResponse


def parameter_type_to_json_schema(param_type: ToolParameterType) -> Dict[str, Any]:
    """Convert Ajentik parameter type to JSON schema type."""
    type_mapping = {
        ToolParameterType.STRING: {"type": "string"},
        ToolParameterType.INTEGER: {"type": "integer"},
        ToolParameterType.FLOAT: {"type": "number"},
        ToolParameterType.BOOLEAN: {"type": "boolean"},
        ToolParameterType.ARRAY: {"type": "array"},
        ToolParameterType.OBJECT: {"type": "object"},
        ToolParameterType.FILE_PATH: {"type": "string", "format": "path"},
        ToolParameterType.URL: {"type": "string", "format": "uri"},
    }
    return type_mapping.get(param_type, {"type": "string"})


def tool_to_mcp(ajentik_tool: Tool) -> MCPTool:
    """Convert an Ajentik tool to MCP tool format."""
    # Build JSON schema for input parameters
    properties = {}
    required = []
    
    for param in ajentik_tool.parameters():
        schema = parameter_type_to_json_schema(param.type)
        
        # Add description if available
        if param.description:
            schema["description"] = param.description
        
        # Add default if available
        if param.default is not None:
            schema["default"] = param.default
        
        # Add constraints if available
        if param.constraints:
            schema.update(param.constraints)
        
        properties[param.name] = schema
        
        if param.required:
            required.append(param.name)
    
    input_schema = {
        "type": "object",
        "properties": properties
    }
    
    if required:
        input_schema["required"] = required
    
    # Add additional properties based on tool safety
    if not ajentik_tool.is_safe:
        input_schema["additionalProperties"] = False
    
    return MCPTool(
        name=ajentik_tool.name,
        description=ajentik_tool.description,
        inputSchema=input_schema
    )


def mcp_to_tool(mcp_tool: MCPTool) -> Tool:
    """Convert an MCP tool to Ajentik tool format."""
    
    class MCPWrappedTool(Tool):
        def __init__(self, mcp_tool_def: MCPTool):
            self._mcp_tool = mcp_tool_def
            super().__init__()
        
        @property
        def name(self) -> str:
            return self._mcp_tool.name
        
        @property
        def description(self) -> str:
            return self._mcp_tool.description or f"MCP tool: {self._mcp_tool.name}"
        
        @property
        def category(self) -> str:
            return "mcp"
        
        @property
        def version(self) -> str:
            return "1.0.0"
        
        @property
        def author(self) -> str:
            return "MCP"
        
        def parameters(self) -> List[ToolParameter]:
            params = []
            schema = self._mcp_tool.inputSchema
            
            if schema.get("type") == "object" and "properties" in schema:
                required_params = schema.get("required", [])
                
                for param_name, param_schema in schema["properties"].items():
                    # Map JSON schema type to ToolParameterType
                    json_type = param_schema.get("type", "string")
                    param_format = param_schema.get("format", "")
                    
                    if json_type == "string":
                        if param_format == "uri":
                            param_type = ToolParameterType.URL
                        elif param_format == "path":
                            param_type = ToolParameterType.FILE_PATH
                        else:
                            param_type = ToolParameterType.STRING
                    elif json_type == "integer":
                        param_type = ToolParameterType.INTEGER
                    elif json_type == "number":
                        param_type = ToolParameterType.FLOAT
                    elif json_type == "boolean":
                        param_type = ToolParameterType.BOOLEAN
                    elif json_type == "array":
                        param_type = ToolParameterType.ARRAY
                    elif json_type == "object":
                        param_type = ToolParameterType.OBJECT
                    else:
                        param_type = ToolParameterType.STRING
                    
                    # Extract constraints
                    constraints = {}
                    for key in ["enum", "minimum", "maximum", "minLength", "maxLength", "pattern"]:
                        if key in param_schema:
                            constraints[key] = param_schema[key]
                    
                    params.append(ToolParameter(
                        name=param_name,
                        type=param_type,
                        description=param_schema.get("description", f"Parameter {param_name}"),
                        required=param_name in required_params,
                        default=param_schema.get("default"),
                        constraints=constraints if constraints else None
                    ))
            
            return params
        
        def execute(self, **kwargs) -> ToolResult:
            # This is a placeholder - actual execution would be handled by MCP client
            return ToolResult(
                success=False,
                error="MCP tool execution not implemented in converter"
            )
    
    return MCPWrappedTool(mcp_tool)


def tool_result_to_mcp(result: ToolResult) -> CallToolResponse:
    """Convert Ajentik ToolResult to MCP CallToolResponse."""
    content = []
    
    if result.success:
        # Convert successful result to MCP content format
        if isinstance(result.data, str):
            content.append({
                "type": "text",
                "text": result.data
            })
        elif isinstance(result.data, bytes):
            # Base64 encode binary data
            import base64
            content.append({
                "type": "resource",
                "resource": {
                    "uri": "data:application/octet-stream",
                    "mimeType": "application/octet-stream",
                    "blob": base64.b64encode(result.data).decode()
                }
            })
        elif isinstance(result.data, dict) and "image" in result.data:
            # Handle image data
            content.append({
                "type": "image",
                "data": result.data["image"],
                "mimeType": result.data.get("mimeType", "image/png")
            })
        else:
            # Convert other data to JSON text
            content.append({
                "type": "text",
                "text": json.dumps(result.data, indent=2) if result.data else ""
            })
    else:
        # Convert error to MCP content
        content.append({
            "type": "text",
            "text": f"Error: {result.error}"
        })
    
    # Add metadata if available
    if result.metadata:
        content.append({
            "type": "text",
            "text": f"Metadata: {json.dumps(result.metadata, indent=2)}"
        })
    
    return CallToolResponse(
        content=content,
        isError=not result.success
    )


def mcp_response_to_tool_result(response: CallToolResponse) -> ToolResult:
    """Convert MCP CallToolResponse to Ajentik ToolResult."""
    if response.isError:
        # Extract error message from content
        error_msg = "MCP tool execution failed"
        for item in response.content:
            if item.get("type") == "text":
                error_msg = item.get("text", error_msg)
                break
        
        return ToolResult(
            success=False,
            error=error_msg
        )
    
    # Extract data from content
    data = {}
    text_contents = []
    
    for item in response.content:
        content_type = item.get("type")
        
        if content_type == "text":
            text_contents.append(item.get("text", ""))
        elif content_type == "image":
            data["image"] = item.get("data")
            data["mimeType"] = item.get("mimeType", "image/png")
        elif content_type == "resource":
            resource = item.get("resource", {})
            data["resource"] = {
                "uri": resource.get("uri"),
                "mimeType": resource.get("mimeType"),
                "blob": resource.get("blob")
            }
    
    # If only text content, return as string
    if len(text_contents) == 1 and not data:
        result_data = text_contents[0]
    elif text_contents:
        data["text"] = "\n".join(text_contents)
        result_data = data
    else:
        result_data = data if data else None
    
    return ToolResult(
        success=True,
        data=result_data
    )


def create_mcp_compatible_tool(name: str, description: str, mcp_client: Any) -> Tool:
    """Create an Ajentik tool that executes via MCP client."""
    
    @tool(
        name=name,
        description=description,
        category="mcp",
        register=False
    )
    async def mcp_tool_wrapper(**kwargs) -> ToolResult:
        """Execute tool via MCP client."""
        try:
            # Call tool through MCP client
            response = await mcp_client.call_tool(name, kwargs)
            
            # Convert MCP response to ToolResult
            return mcp_response_to_tool_result(response)
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"MCP tool execution failed: {str(e)}"
            )
    
    return mcp_tool_wrapper.tool