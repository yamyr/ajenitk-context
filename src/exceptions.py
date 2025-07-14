"""Custom exceptions for Ajentik.

This module defines the exception hierarchy used throughout the Ajentik codebase.
All custom exceptions inherit from AjentikError for consistent error handling.
"""

from typing import Optional, Dict, Any


class AjentikError(Exception):
    """Base exception for all Ajentik-specific errors.
    
    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ToolError(AjentikError):
    """Base exception for tool-related errors."""
    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails.
    
    Attributes:
        tool_name: Name of the tool that failed
        original_error: The original exception that caused the failure
    """
    
    def __init__(self, tool_name: str, message: str, 
                 original_error: Optional[Exception] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.tool_name = tool_name
        self.original_error = original_error


class ToolValidationError(ToolError):
    """Raised when tool parameter validation fails.
    
    Attributes:
        parameter_name: Name of the invalid parameter
        expected_type: Expected parameter type
        actual_value: The actual value provided
    """
    
    def __init__(self, parameter_name: str, expected_type: str, 
                 actual_value: Any, message: Optional[str] = None):
        msg = message or f"Invalid parameter '{parameter_name}': expected {expected_type}, got {type(actual_value).__name__}"
        super().__init__(msg)
        self.parameter_name = parameter_name
        self.expected_type = expected_type
        self.actual_value = actual_value


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found in the registry."""
    
    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found in registry")
        self.tool_name = tool_name


class MCPError(AjentikError):
    """Base exception for MCP-related errors."""
    pass


class MCPCommunicationError(MCPError):
    """Raised when MCP communication fails.
    
    Attributes:
        method: The MCP method that failed
        request_id: Optional request ID
    """
    
    def __init__(self, message: str, method: Optional[str] = None, 
                 request_id: Optional[int] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.method = method
        self.request_id = request_id


class MCPTimeoutError(MCPCommunicationError):
    """Raised when an MCP request times out."""
    
    def __init__(self, method: str, timeout: float):
        super().__init__(
            f"MCP request '{method}' timed out after {timeout} seconds",
            method=method
        )
        self.timeout = timeout


class MCPProtocolError(MCPError):
    """Raised when MCP protocol violations occur."""
    pass


class ConfigurationError(AjentikError):
    """Raised when configuration is invalid or missing."""
    pass


class SecurityError(AjentikError):
    """Raised when security constraints are violated.
    
    Attributes:
        security_level: The current security level
        attempted_action: The action that was blocked
    """
    
    def __init__(self, message: str, security_level: str, 
                 attempted_action: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.security_level = security_level
        self.attempted_action = attempted_action