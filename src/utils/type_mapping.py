"""Type mapping utilities for converting between Python types and ToolParameterType.

This module provides centralized type conversion functions to avoid duplication
across the codebase.
"""

from typing import Any, Type, Union, get_origin, get_args
import inspect
from enum import Enum

from ..tools.base import ToolParameterType


class TypeMappingError(Exception):
    """Raised when type mapping fails."""
    pass


def python_type_to_parameter_type(annotation: Any) -> ToolParameterType:
    """Map Python type annotations to ToolParameterType.
    
    Args:
        annotation: Python type annotation (e.g., str, List[int], Optional[bool])
        
    Returns:
        Corresponding ToolParameterType
        
    Raises:
        TypeMappingError: When type cannot be mapped
    """
    # Handle None/Any
    if annotation is None or annotation is Any:
        return ToolParameterType.STRING
    
    # Direct type mapping
    type_map = {
        str: ToolParameterType.STRING,
        int: ToolParameterType.INTEGER,
        float: ToolParameterType.FLOAT,
        bool: ToolParameterType.BOOLEAN,
        list: ToolParameterType.ARRAY,
        dict: ToolParameterType.OBJECT,
    }
    
    # Check direct mapping first
    if annotation in type_map:
        return type_map[annotation]
    
    # Handle Optional types (Union[X, None])
    origin = get_origin(annotation)
    args = get_args(annotation)
    
    if origin is Union:
        # Check if it's Optional (Union with None)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            # It's Optional[T], recursively map T
            return python_type_to_parameter_type(non_none_args[0])
        # For other unions, default to STRING
        return ToolParameterType.STRING
    
    # Handle generic types (List[X], Dict[X, Y], etc.)
    if origin is not None:
        if origin in type_map:
            return type_map[origin]
        # Handle typing aliases
        if origin is list:
            return ToolParameterType.ARRAY
        if origin is dict:
            return ToolParameterType.OBJECT
    
    # Handle string annotations (forward references)
    if isinstance(annotation, str):
        # Try to evaluate the string
        try:
            evaluated = eval(annotation, globals(), locals())
            return python_type_to_parameter_type(evaluated)
        except:
            # Default to STRING for unresolvable string annotations
            return ToolParameterType.STRING
    
    # Default to STRING for unknown types
    return ToolParameterType.STRING


def parameter_type_to_python_type(param_type: ToolParameterType) -> Type:
    """Convert ToolParameterType to Python type.
    
    Args:
        param_type: ToolParameterType enum value
        
    Returns:
        Corresponding Python type
    """
    type_map = {
        ToolParameterType.STRING: str,
        ToolParameterType.INTEGER: int,
        ToolParameterType.FLOAT: float,
        ToolParameterType.BOOLEAN: bool,
        ToolParameterType.ARRAY: list,
        ToolParameterType.OBJECT: dict,
    }
    
    return type_map.get(param_type, str)


def get_type_description(param_type: ToolParameterType) -> str:
    """Get human-readable description of a parameter type.
    
    Args:
        param_type: ToolParameterType enum value
        
    Returns:
        Human-readable type description
    """
    descriptions = {
        ToolParameterType.STRING: "string",
        ToolParameterType.INTEGER: "integer",
        ToolParameterType.FLOAT: "floating-point number",
        ToolParameterType.BOOLEAN: "boolean (true/false)",
        ToolParameterType.ARRAY: "array/list",
        ToolParameterType.OBJECT: "object/dictionary",
    }
    
    return descriptions.get(param_type, "unknown type")


def infer_type_from_value(value: Any) -> ToolParameterType:
    """Infer ToolParameterType from a runtime value.
    
    Args:
        value: Runtime value to infer type from
        
    Returns:
        Inferred ToolParameterType
    """
    if isinstance(value, bool):
        # Check bool before int since bool is a subclass of int
        return ToolParameterType.BOOLEAN
    elif isinstance(value, int):
        return ToolParameterType.INTEGER
    elif isinstance(value, float):
        return ToolParameterType.FLOAT
    elif isinstance(value, str):
        return ToolParameterType.STRING
    elif isinstance(value, list):
        return ToolParameterType.ARRAY
    elif isinstance(value, dict):
        return ToolParameterType.OBJECT
    else:
        # Default to STRING for unknown types
        return ToolParameterType.STRING


def validate_type_match(value: Any, expected_type: ToolParameterType) -> bool:
    """Check if a value matches the expected parameter type.
    
    Args:
        value: Value to check
        expected_type: Expected ToolParameterType
        
    Returns:
        True if value matches expected type, False otherwise
    """
    python_type = parameter_type_to_python_type(expected_type)
    
    # Special handling for numeric types
    if expected_type == ToolParameterType.FLOAT and isinstance(value, (int, float)):
        return True
    
    # Special handling for OBJECT - accept any dict-like object
    if expected_type == ToolParameterType.OBJECT:
        return hasattr(value, '__getitem__') and hasattr(value, 'keys')
    
    # Special handling for ARRAY - accept any iterable except strings
    if expected_type == ToolParameterType.ARRAY:
        return hasattr(value, '__iter__') and not isinstance(value, (str, bytes))
    
    return isinstance(value, python_type)