"""Validation utilities for parameters and data types.

This module provides comprehensive validation functions used throughout
the Ajentik codebase.
"""

from typing import Any, Dict, List, Optional, Set, Union, Type
import re
from pathlib import Path

from ..exceptions import ToolValidationError
from ..tools.base import ToolParameter, ToolParameterType
from .type_mapping import validate_type_match, get_type_description


def validate_type(value: Any, expected_type: ToolParameterType, 
                 parameter_name: str) -> None:
    """Validate that a value matches the expected type.
    
    Args:
        value: Value to validate
        expected_type: Expected ToolParameterType
        parameter_name: Name of the parameter (for error messages)
        
    Raises:
        ToolValidationError: If validation fails
    """
    if not validate_type_match(value, expected_type):
        raise ToolValidationError(
            parameter_name=parameter_name,
            expected_type=get_type_description(expected_type),
            actual_value=value
        )


def validate_parameters(parameters: Dict[str, Any], 
                       parameter_specs: List[ToolParameter]) -> Dict[str, Any]:
    """Validate and normalize parameters against specifications.
    
    Args:
        parameters: Raw parameter dictionary
        parameter_specs: List of ToolParameter specifications
        
    Returns:
        Validated and normalized parameters
        
    Raises:
        ToolValidationError: If validation fails
    """
    validated = {}
    param_map = {p.name: p for p in parameter_specs}
    
    # Check for unknown parameters
    known_params = {p.name for p in parameter_specs}
    unknown_params = set(parameters.keys()) - known_params
    if unknown_params:
        raise ToolValidationError(
            parameter_name=", ".join(unknown_params),
            expected_type="known parameters",
            actual_value=unknown_params,
            message=f"Unknown parameters: {', '.join(unknown_params)}"
        )
    
    # Validate each parameter
    for param_spec in parameter_specs:
        param_name = param_spec.name
        
        if param_name in parameters:
            value = parameters[param_name]
            
            # Type validation
            validate_type(value, param_spec.type, param_name)
            
            # Additional validations
            if param_spec.type == ToolParameterType.STRING:
                validated[param_name] = validate_string(
                    value, param_name, param_spec.description
                )
            elif param_spec.type == ToolParameterType.INTEGER:
                validated[param_name] = validate_integer(
                    value, param_name, param_spec.description
                )
            elif param_spec.type == ToolParameterType.FLOAT:
                validated[param_name] = validate_float(
                    value, param_name, param_spec.description
                )
            elif param_spec.type == ToolParameterType.ARRAY:
                validated[param_name] = validate_array(
                    value, param_name, param_spec.description
                )
            elif param_spec.type == ToolParameterType.OBJECT:
                validated[param_name] = validate_object(
                    value, param_name, param_spec.description
                )
            else:
                validated[param_name] = value
                
        elif param_spec.required:
            # Check for default value
            if hasattr(param_spec, 'default'):
                validated[param_name] = param_spec.default
            else:
                raise ToolValidationError(
                    parameter_name=param_name,
                    expected_type=get_type_description(param_spec.type),
                    actual_value=None,
                    message=f"Required parameter '{param_name}' is missing"
                )
    
    return validated


def validate_string(value: str, param_name: str, 
                   description: Optional[str] = None) -> str:
    """Validate and normalize string parameter.
    
    Args:
        value: String value
        param_name: Parameter name
        description: Parameter description (may contain validation hints)
        
    Returns:
        Validated string
        
    Raises:
        ToolValidationError: If validation fails
    """
    # Check for empty strings if required
    if description and "non-empty" in description.lower() and not value.strip():
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type="non-empty string",
            actual_value=value,
            message=f"Parameter '{param_name}' must be non-empty"
        )
    
    # Check for path validation
    if description and any(word in description.lower() for word in ["path", "file", "directory"]):
        # Basic path validation
        try:
            path = Path(value)
            # Check for path traversal attempts
            if ".." in path.parts:
                raise ToolValidationError(
                    parameter_name=param_name,
                    expected_type="safe path",
                    actual_value=value,
                    message=f"Path traversal not allowed in '{param_name}'"
                )
        except Exception as e:
            raise ToolValidationError(
                parameter_name=param_name,
                expected_type="valid path",
                actual_value=value,
                message=f"Invalid path in '{param_name}': {str(e)}"
            )
    
    # Check for pattern validation
    if description and "pattern:" in description:
        # Extract pattern from description
        pattern_match = re.search(r'pattern:\s*([^\s]+)', description)
        if pattern_match:
            pattern = pattern_match.group(1)
            if not re.match(pattern, value):
                raise ToolValidationError(
                    parameter_name=param_name,
                    expected_type=f"string matching pattern {pattern}",
                    actual_value=value
                )
    
    return value.strip()


def validate_integer(value: Union[int, float], param_name: str,
                    description: Optional[str] = None) -> int:
    """Validate and normalize integer parameter.
    
    Args:
        value: Integer value
        param_name: Parameter name
        description: Parameter description (may contain range hints)
        
    Returns:
        Validated integer
        
    Raises:
        ToolValidationError: If validation fails
    """
    # Convert float to int if it's a whole number
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    
    if not isinstance(value, int):
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type="integer",
            actual_value=value
        )
    
    # Check for range validation in description
    if description:
        # Check for minimum value
        min_match = re.search(r'min[:\s]+(-?\d+)', description, re.IGNORECASE)
        if min_match:
            min_val = int(min_match.group(1))
            if value < min_val:
                raise ToolValidationError(
                    parameter_name=param_name,
                    expected_type=f"integer >= {min_val}",
                    actual_value=value
                )
        
        # Check for maximum value
        max_match = re.search(r'max[:\s]+(-?\d+)', description, re.IGNORECASE)
        if max_match:
            max_val = int(max_match.group(1))
            if value > max_val:
                raise ToolValidationError(
                    parameter_name=param_name,
                    expected_type=f"integer <= {max_val}",
                    actual_value=value
                )
    
    return value


def validate_float(value: Union[int, float], param_name: str,
                  description: Optional[str] = None) -> float:
    """Validate and normalize float parameter.
    
    Args:
        value: Float value
        param_name: Parameter name
        description: Parameter description
        
    Returns:
        Validated float
        
    Raises:
        ToolValidationError: If validation fails
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type="float",
            actual_value=value
        )
    
    # Check for special float values
    if description and "positive" in description.lower() and value <= 0:
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type="positive float",
            actual_value=value
        )
    
    return value


def validate_array(value: List[Any], param_name: str,
                  description: Optional[str] = None) -> List[Any]:
    """Validate array parameter.
    
    Args:
        value: Array value
        param_name: Parameter name
        description: Parameter description
        
    Returns:
        Validated array
        
    Raises:
        ToolValidationError: If validation fails
    """
    if not isinstance(value, list):
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type="array",
            actual_value=value
        )
    
    # Check for non-empty constraint
    if description and "non-empty" in description.lower() and len(value) == 0:
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type="non-empty array",
            actual_value=value
        )
    
    return value


def validate_object(value: Dict[str, Any], param_name: str,
                   description: Optional[str] = None) -> Dict[str, Any]:
    """Validate object/dictionary parameter.
    
    Args:
        value: Dictionary value
        param_name: Parameter name
        description: Parameter description
        
    Returns:
        Validated dictionary
        
    Raises:
        ToolValidationError: If validation fails
    """
    if not isinstance(value, dict):
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type="object",
            actual_value=value
        )
    
    return value


def validate_enum(value: Any, allowed_values: Set[Any], 
                 param_name: str) -> Any:
    """Validate that a value is in a set of allowed values.
    
    Args:
        value: Value to validate
        allowed_values: Set of allowed values
        param_name: Parameter name
        
    Returns:
        Validated value
        
    Raises:
        ToolValidationError: If value not in allowed set
    """
    if value not in allowed_values:
        raise ToolValidationError(
            parameter_name=param_name,
            expected_type=f"one of {allowed_values}",
            actual_value=value
        )
    
    return value