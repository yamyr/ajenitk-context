"""Tests for utility modules."""

import pytest
import asyncio
import time
from typing import Optional, List, Union

from src.utils.retry import (
    retry_async, retry_sync, with_retry, RetryError
)
from src.utils.type_mapping import (
    python_type_to_parameter_type, parameter_type_to_python_type,
    get_type_description, infer_type_from_value, validate_type_match
)
from src.utils.validation import (
    validate_type, validate_parameters, validate_string,
    validate_integer, validate_float, validate_array,
    validate_object, validate_enum
)
from src.tools.base_refactored import ToolParameter, ToolParameterType
from src.exceptions import ToolValidationError


class TestRetry:
    """Test retry utilities."""
    
    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test async retry with successful execution."""
        call_count = 0
        
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await retry_async(
            flaky_function,
            max_attempts=5,
            initial_delay=0.01,
            exceptions=(ConnectionError,)
        )
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_async_all_fail(self):
        """Test async retry when all attempts fail."""
        async def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(RetryError) as exc_info:
            await retry_async(
                always_fails,
                max_attempts=3,
                initial_delay=0.01,
                exceptions=(ValueError,)
            )
        
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_error, ValueError)
    
    def test_retry_sync_success(self):
        """Test sync retry with successful execution."""
        call_count = 0
        
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary failure")
            return "success"
        
        result = retry_sync(
            flaky_function,
            max_attempts=3,
            initial_delay=0.01,
            exceptions=(RuntimeError,)
        )
        
        assert result == "success"
        assert call_count == 2
    
    def test_retry_sync_specific_exceptions(self):
        """Test retry only catches specified exceptions."""
        def raises_value_error():
            raise ValueError("Not retryable")
        
        # Should not retry ValueError when only RuntimeError is specified
        with pytest.raises(ValueError):
            retry_sync(
                raises_value_error,
                max_attempts=3,
                exceptions=(RuntimeError,)
            )
    
    def test_with_retry_decorator_sync(self):
        """Test @with_retry decorator on sync function."""
        call_count = 0
        
        @with_retry(max_attempts=3, initial_delay=0.01)
        def flaky_func(value: int) -> int:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary")
            return value * 2
        
        result = flaky_func(5)
        assert result == 10
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_with_retry_decorator_async(self):
        """Test @with_retry decorator on async function."""
        call_count = 0
        
        @with_retry(
            max_attempts=4,
            initial_delay=0.01,
            exceptions=(ConnectionError,)
        )
        async def async_flaky(value: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network issue")
            await asyncio.sleep(0.01)
            return value.upper()
        
        result = await async_flaky("hello")
        assert result == "HELLO"
        assert call_count == 3
    
    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        start_time = time.time()
        attempt_times = []
        
        def track_time():
            attempt_times.append(time.time() - start_time)
            raise Exception("Always fail")
        
        try:
            retry_sync(
                track_time,
                max_attempts=3,
                initial_delay=0.1,
                backoff_factor=2.0
            )
        except RetryError:
            pass
        
        # Check delays increase exponentially
        assert len(attempt_times) == 3
        # First attempt is immediate
        assert attempt_times[0] < 0.05
        # Second attempt after ~0.1s
        assert 0.05 < attempt_times[1] < 0.15
        # Third attempt after ~0.3s (0.1 + 0.2)
        assert 0.25 < attempt_times[2] < 0.35


class TestTypeMapping:
    """Test type mapping utilities."""
    
    def test_python_type_to_parameter_type(self):
        """Test mapping Python types to ToolParameterType."""
        assert python_type_to_parameter_type(str) == ToolParameterType.STRING
        assert python_type_to_parameter_type(int) == ToolParameterType.INTEGER
        assert python_type_to_parameter_type(float) == ToolParameterType.FLOAT
        assert python_type_to_parameter_type(bool) == ToolParameterType.BOOLEAN
        assert python_type_to_parameter_type(list) == ToolParameterType.ARRAY
        assert python_type_to_parameter_type(dict) == ToolParameterType.OBJECT
    
    def test_generic_type_mapping(self):
        """Test mapping generic types."""
        assert python_type_to_parameter_type(List[str]) == ToolParameterType.ARRAY
        assert python_type_to_parameter_type(Optional[int]) == ToolParameterType.INTEGER
        assert python_type_to_parameter_type(Union[str, None]) == ToolParameterType.STRING
    
    def test_unknown_type_mapping(self):
        """Test unknown types default to STRING."""
        class CustomClass:
            pass
        
        assert python_type_to_parameter_type(CustomClass) == ToolParameterType.STRING
        assert python_type_to_parameter_type(None) == ToolParameterType.STRING
    
    def test_parameter_type_to_python_type(self):
        """Test mapping ToolParameterType to Python types."""
        assert parameter_type_to_python_type(ToolParameterType.STRING) == str
        assert parameter_type_to_python_type(ToolParameterType.INTEGER) == int
        assert parameter_type_to_python_type(ToolParameterType.FLOAT) == float
        assert parameter_type_to_python_type(ToolParameterType.BOOLEAN) == bool
        assert parameter_type_to_python_type(ToolParameterType.ARRAY) == list
        assert parameter_type_to_python_type(ToolParameterType.OBJECT) == dict
    
    def test_get_type_description(self):
        """Test getting human-readable type descriptions."""
        assert get_type_description(ToolParameterType.STRING) == "string"
        assert get_type_description(ToolParameterType.INTEGER) == "integer"
        assert get_type_description(ToolParameterType.FLOAT) == "floating-point number"
        assert get_type_description(ToolParameterType.BOOLEAN) == "boolean (true/false)"
        assert get_type_description(ToolParameterType.ARRAY) == "array/list"
        assert get_type_description(ToolParameterType.OBJECT) == "object/dictionary"
    
    def test_infer_type_from_value(self):
        """Test inferring type from runtime values."""
        assert infer_type_from_value("hello") == ToolParameterType.STRING
        assert infer_type_from_value(42) == ToolParameterType.INTEGER
        assert infer_type_from_value(3.14) == ToolParameterType.FLOAT
        assert infer_type_from_value(True) == ToolParameterType.BOOLEAN
        assert infer_type_from_value([1, 2, 3]) == ToolParameterType.ARRAY
        assert infer_type_from_value({"key": "value"}) == ToolParameterType.OBJECT
    
    def test_validate_type_match(self):
        """Test type validation."""
        assert validate_type_match("hello", ToolParameterType.STRING) is True
        assert validate_type_match(42, ToolParameterType.INTEGER) is True
        assert validate_type_match(3.14, ToolParameterType.FLOAT) is True
        assert validate_type_match(True, ToolParameterType.BOOLEAN) is True
        assert validate_type_match([1, 2], ToolParameterType.ARRAY) is True
        assert validate_type_match({}, ToolParameterType.OBJECT) is True
        
        # Type mismatches
        assert validate_type_match("123", ToolParameterType.INTEGER) is False
        assert validate_type_match(123, ToolParameterType.STRING) is False
        
        # Special cases
        assert validate_type_match(42, ToolParameterType.FLOAT) is True  # int accepted as float
        assert validate_type_match((1, 2, 3), ToolParameterType.ARRAY) is True  # tuple as array


class TestValidation:
    """Test validation utilities."""
    
    def test_validate_type_success(self):
        """Test successful type validation."""
        # Should not raise
        validate_type("hello", ToolParameterType.STRING, "test_param")
        validate_type(42, ToolParameterType.INTEGER, "test_param")
        validate_type(True, ToolParameterType.BOOLEAN, "test_param")
    
    def test_validate_type_failure(self):
        """Test type validation failures."""
        with pytest.raises(ToolValidationError) as exc_info:
            validate_type("not_a_number", ToolParameterType.INTEGER, "count")
        
        assert exc_info.value.parameter_name == "count"
        assert exc_info.value.expected_type == "integer"
        assert exc_info.value.actual_value == "not_a_number"
    
    def test_validate_parameters_success(self):
        """Test successful parameter validation."""
        params = [
            ToolParameter(
                name="name",
                type=ToolParameterType.STRING,
                description="Name",
                required=True
            ),
            ToolParameter(
                name="age",
                type=ToolParameterType.INTEGER,
                description="Age",
                required=False,
                default=0
            )
        ]
        
        # All parameters provided
        validated = validate_parameters(
            {"name": "John", "age": 30},
            params
        )
        assert validated == {"name": "John", "age": 30}
        
        # Optional parameter omitted
        validated = validate_parameters(
            {"name": "Jane"},
            params
        )
        assert validated == {"name": "Jane", "age": 0}
    
    def test_validate_parameters_missing_required(self):
        """Test missing required parameter."""
        params = [
            ToolParameter(
                name="required_field",
                type=ToolParameterType.STRING,
                description="Required",
                required=True
            )
        ]
        
        with pytest.raises(ToolValidationError, match="required"):
            validate_parameters({}, params)
    
    def test_validate_parameters_unknown(self):
        """Test unknown parameters are rejected."""
        params = [
            ToolParameter(
                name="known",
                type=ToolParameterType.STRING,
                description="Known parameter"
            )
        ]
        
        with pytest.raises(ToolValidationError, match="Unknown parameters"):
            validate_parameters(
                {"known": "value", "unknown": "value"},
                params
            )
    
    def test_validate_string(self):
        """Test string validation."""
        # Basic validation
        assert validate_string("  hello  ", "test", None) == "hello"
        
        # Non-empty validation
        with pytest.raises(ToolValidationError, match="non-empty"):
            validate_string("  ", "test", "non-empty string required")
        
        # Path validation
        with pytest.raises(ToolValidationError, match="Path traversal"):
            validate_string("../etc/passwd", "file", "file path")
        
        # Pattern validation
        result = validate_string(
            "abc123",
            "code",
            "pattern: ^[a-z]+[0-9]+$"
        )
        assert result == "abc123"
        
        with pytest.raises(ToolValidationError):
            validate_string(
                "123abc",
                "code",
                "pattern: ^[a-z]+[0-9]+$"
            )
    
    def test_validate_integer(self):
        """Test integer validation."""
        # Basic validation
        assert validate_integer(42, "test", None) == 42
        assert validate_integer(42.0, "test", None) == 42  # Float to int
        
        # Range validation
        assert validate_integer(5, "test", "min: 0 max: 10") == 5
        
        with pytest.raises(ToolValidationError, match=">="):
            validate_integer(-5, "test", "min: 0")
        
        with pytest.raises(ToolValidationError, match="<="):
            validate_integer(15, "test", "max: 10")
    
    def test_validate_float(self):
        """Test float validation."""
        assert validate_float(3.14, "test", None) == 3.14
        assert validate_float(42, "test", None) == 42.0  # Int to float
        
        # Positive constraint
        with pytest.raises(ToolValidationError, match="positive"):
            validate_float(-1.5, "test", "positive value required")
    
    def test_validate_array(self):
        """Test array validation."""
        assert validate_array([1, 2, 3], "test", None) == [1, 2, 3]
        
        # Non-empty constraint
        with pytest.raises(ToolValidationError, match="non-empty"):
            validate_array([], "test", "non-empty array required")
        
        # Type check
        with pytest.raises(ToolValidationError):
            validate_array("not_a_list", "test", None)
    
    def test_validate_object(self):
        """Test object/dict validation."""
        assert validate_object({"key": "value"}, "test", None) == {"key": "value"}
        
        # Type check
        with pytest.raises(ToolValidationError):
            validate_object([1, 2, 3], "test", None)
    
    def test_validate_enum(self):
        """Test enum validation."""
        allowed = {"red", "green", "blue"}
        
        assert validate_enum("red", allowed, "color") == "red"
        
        with pytest.raises(ToolValidationError, match="one of"):
            validate_enum("yellow", allowed, "color")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])