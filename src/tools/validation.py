"""Tool validation and sandboxing utilities."""

import os
import re
import ast
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum
import logging

from .base import Tool, ToolParameter, ToolParameterType, ToolError


logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for tool execution."""
    UNRESTRICTED = "unrestricted"  # No restrictions
    SAFE = "safe"                   # Basic safety checks
    SANDBOXED = "sandboxed"         # Full sandboxing
    RESTRICTED = "restricted"       # High restrictions


class ToolValidator:
    """Validates tools for safety and correctness."""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.SAFE):
        self.security_level = security_level
        self.blocked_modules = {
            'os', 'subprocess', 'sys', '__builtins__',
            'eval', 'exec', 'compile', '__import__'
        }
        self.allowed_paths: Set[Path] = set()
        self.validation_rules: List[Callable] = []
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default validation rules based on security level."""
        if self.security_level == SecurityLevel.SAFE:
            self.add_rule(self._check_safe_imports)
            self.add_rule(self._check_file_access)
        elif self.security_level == SecurityLevel.SANDBOXED:
            self.add_rule(self._check_safe_imports)
            self.add_rule(self._check_file_access)
            self.add_rule(self._check_network_access)
            self.add_rule(self._check_system_calls)
        elif self.security_level == SecurityLevel.RESTRICTED:
            self.add_rule(self._check_safe_imports)
            self.add_rule(self._check_file_access)
            self.add_rule(self._check_network_access)
            self.add_rule(self._check_system_calls)
            self.add_rule(self._check_code_injection)
    
    def add_allowed_path(self, path: Path):
        """Add a path to the allowed list for file operations."""
        self.allowed_paths.add(Path(path).resolve())
    
    def add_rule(self, rule: Callable):
        """Add a custom validation rule."""
        self.validation_rules.append(rule)
    
    def validate_tool(self, tool: Tool) -> Dict[str, Any]:
        """Validate a tool for safety and correctness.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "security_level": self.security_level.value
        }
        
        # Check tool metadata
        if not tool.name:
            results["errors"].append("Tool must have a name")
            results["valid"] = False
        
        if not tool.description:
            results["warnings"].append("Tool should have a description")
        
        # Validate parameters
        param_results = self._validate_parameters(tool.parameters())
        if param_results["errors"]:
            results["errors"].extend(param_results["errors"])
            results["valid"] = False
        results["warnings"].extend(param_results["warnings"])
        
        # Run security checks if not unrestricted
        if self.security_level != SecurityLevel.UNRESTRICTED:
            security_results = self._run_security_checks(tool)
            if security_results["errors"]:
                results["errors"].extend(security_results["errors"])
                results["valid"] = False
            results["warnings"].extend(security_results["warnings"])
        
        # Run custom validation rules
        for rule in self.validation_rules:
            try:
                rule_results = rule(tool)
                if rule_results.get("errors"):
                    results["errors"].extend(rule_results["errors"])
                    results["valid"] = False
                if rule_results.get("warnings"):
                    results["warnings"].extend(rule_results["warnings"])
            except Exception as e:
                results["warnings"].append(f"Validation rule failed: {e}")
        
        return results
    
    def _validate_parameters(self, parameters: List[ToolParameter]) -> Dict[str, List[str]]:
        """Validate tool parameters."""
        errors = []
        warnings = []
        
        param_names = set()
        
        for param in parameters:
            # Check for duplicate names
            if param.name in param_names:
                errors.append(f"Duplicate parameter name: {param.name}")
            param_names.add(param.name)
            
            # Validate parameter name
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', param.name):
                errors.append(f"Invalid parameter name: {param.name}")
            
            # Check type constraints
            if param.type == ToolParameterType.FILE_PATH and param.constraints:
                if "allowed_extensions" in param.constraints:
                    exts = param.constraints["allowed_extensions"]
                    if not isinstance(exts, list):
                        errors.append(f"allowed_extensions must be a list for {param.name}")
            
            # Warn about missing descriptions
            if not param.description or param.description == f"Parameter {param.name}":
                warnings.append(f"Parameter {param.name} should have a meaningful description")
        
        return {"errors": errors, "warnings": warnings}
    
    def _run_security_checks(self, tool: Tool) -> Dict[str, List[str]]:
        """Run security checks on the tool."""
        errors = []
        warnings = []
        
        # Get the source code if possible
        try:
            source = inspect.getsource(tool.execute)
            
            # Parse the AST
            tree = ast.parse(source)
            
            # Check for dangerous imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.blocked_modules:
                            errors.append(f"Tool imports blocked module: {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module in self.blocked_modules:
                        errors.append(f"Tool imports from blocked module: {node.module}")
            
        except Exception as e:
            warnings.append(f"Could not analyze tool source: {e}")
        
        # Check tool safety flags
        if not tool.is_safe and self.security_level == SecurityLevel.SAFE:
            warnings.append("Tool is marked as unsafe")
        
        if tool.requires_confirmation and self.security_level != SecurityLevel.UNRESTRICTED:
            warnings.append("Tool requires user confirmation")
        
        return {"errors": errors, "warnings": warnings}
    
    def _check_safe_imports(self, tool: Tool) -> Dict[str, List[str]]:
        """Check for safe imports only."""
        errors = []
        warnings = []
        
        # This is already done in _run_security_checks
        # Additional checks can be added here
        
        return {"errors": errors, "warnings": warnings}
    
    def _check_file_access(self, tool: Tool) -> Dict[str, List[str]]:
        """Check file access patterns."""
        errors = []
        warnings = []
        
        # Check if tool has file path parameters
        for param in tool.parameters():
            if param.type == ToolParameterType.FILE_PATH:
                if not self.allowed_paths:
                    warnings.append(f"Tool has file access but no allowed paths configured")
                else:
                    warnings.append(f"Tool can access files - ensure paths are validated")
        
        return {"errors": errors, "warnings": warnings}
    
    def _check_network_access(self, tool: Tool) -> Dict[str, List[str]]:
        """Check for network access."""
        errors = []
        warnings = []
        
        try:
            source = inspect.getsource(tool.execute)
            
            # Look for network-related imports
            network_modules = ['urllib', 'requests', 'httpx', 'aiohttp', 'socket']
            for module in network_modules:
                if module in source:
                    warnings.append(f"Tool may perform network access via {module}")
            
            # Check for URL parameters
            for param in tool.parameters():
                if param.type == ToolParameterType.URL:
                    warnings.append(f"Tool accepts URL parameter: {param.name}")
        
        except:
            pass
        
        return {"errors": errors, "warnings": warnings}
    
    def _check_system_calls(self, tool: Tool) -> Dict[str, List[str]]:
        """Check for system calls."""
        errors = []
        warnings = []
        
        dangerous_calls = [
            'subprocess', 'os.system', 'os.popen', 'os.exec',
            'eval', 'exec', 'compile', '__import__'
        ]
        
        try:
            source = inspect.getsource(tool.execute)
            
            for call in dangerous_calls:
                if call in source:
                    errors.append(f"Tool contains potentially dangerous call: {call}")
        
        except:
            pass
        
        return {"errors": errors, "warnings": warnings}
    
    def _check_code_injection(self, tool: Tool) -> Dict[str, List[str]]:
        """Check for code injection vulnerabilities."""
        errors = []
        warnings = []
        
        injection_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            r'__import__\s*\(',
            r'\.format\s*\([^)]*\{[^}]*\}',  # String format with user input
            r'%\s*\([^)]*\)',  # Old string formatting
        ]
        
        try:
            source = inspect.getsource(tool.execute)
            
            for pattern in injection_patterns:
                if re.search(pattern, source):
                    warnings.append(f"Tool may be vulnerable to code injection: {pattern}")
        
        except:
            pass
        
        return {"errors": errors, "warnings": warnings}


class ToolSandbox:
    """Provides sandboxed execution environment for tools."""
    
    def __init__(self, validator: Optional[ToolValidator] = None):
        self.validator = validator or ToolValidator(SecurityLevel.SANDBOXED)
        self.resource_limits = {
            "max_memory": 100 * 1024 * 1024,  # 100MB
            "max_cpu_time": 30,  # 30 seconds
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "max_open_files": 10
        }
    
    def set_resource_limit(self, resource: str, limit: Any):
        """Set a resource limit."""
        self.resource_limits[resource] = limit
    
    def validate_path(self, path: Path) -> bool:
        """Check if a path is allowed."""
        path = Path(path).resolve()
        
        # Check against allowed paths
        for allowed in self.validator.allowed_paths:
            try:
                path.relative_to(allowed)
                return True
            except ValueError:
                continue
        
        return False
    
    def sanitize_parameters(self, tool: Tool, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize parameters before execution."""
        sanitized = {}
        
        for param_def in tool.parameters():
            param_name = param_def.name
            
            if param_name not in parameters:
                continue
            
            value = parameters[param_name]
            
            # Sanitize based on type
            if param_def.type == ToolParameterType.FILE_PATH:
                # Validate file path
                path = Path(value)
                if not self.validate_path(path):
                    raise ToolError(f"Access denied to path: {value}")
                sanitized[param_name] = str(path.resolve())
            
            elif param_def.type == ToolParameterType.STRING:
                # Basic string sanitization
                sanitized[param_name] = str(value)[:10000]  # Limit length
            
            elif param_def.type == ToolParameterType.URL:
                # Validate URL format
                if not re.match(r'^https?://', value):
                    raise ToolError(f"Invalid URL format: {value}")
                sanitized[param_name] = value
            
            else:
                # Pass through other types
                sanitized[param_name] = value
        
        return sanitized
    
    def execute_sandboxed(self, tool: Tool, **kwargs):
        """Execute a tool in a sandboxed environment."""
        # Validate the tool first
        validation_results = self.validator.validate_tool(tool)
        if not validation_results["valid"]:
            raise ToolError(
                f"Tool validation failed: {'; '.join(validation_results['errors'])}"
            )
        
        # Sanitize parameters
        sanitized_params = self.sanitize_parameters(tool, kwargs)
        
        # Apply resource limits (platform-specific implementation needed)
        # This is a simplified version - real sandboxing would use OS-level controls
        
        try:
            import signal
            import resource
            
            # Set CPU time limit
            def timeout_handler(signum, frame):
                raise ToolError("Tool execution timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.resource_limits["max_cpu_time"])
            
            # Set memory limit (Unix only)
            if hasattr(resource, 'RLIMIT_AS'):
                resource.setrlimit(
                    resource.RLIMIT_AS,
                    (self.resource_limits["max_memory"], self.resource_limits["max_memory"])
                )
            
            # Execute the tool
            result = tool(**sanitized_params)
            
            # Cancel alarm
            signal.alarm(0)
            
            return result
            
        except Exception as e:
            signal.alarm(0)  # Cancel alarm
            raise
        
        # Note: This is a basic implementation. Production sandboxing would use:
        # - Container technology (Docker, etc.)
        # - Process isolation (seccomp, AppArmor, SELinux)
        # - Virtual environments
        # - Resource cgroups


def validate_tool_safety(tool: Tool, level: SecurityLevel = SecurityLevel.SAFE) -> bool:
    """Quick function to validate tool safety.
    
    Returns:
        True if tool passes validation
    """
    validator = ToolValidator(level)
    results = validator.validate_tool(tool)
    return results["valid"]