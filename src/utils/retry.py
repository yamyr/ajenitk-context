"""Retry utilities with exponential backoff.

This module provides retry decorators for both synchronous and asynchronous
functions with configurable backoff strategies.
"""

import asyncio
import functools
import time
from typing import Callable, Tuple, Type, TypeVar, Union, Optional, Any
from typing import overload

from ..exceptions import AjentikError

T = TypeVar('T')


class RetryError(AjentikError):
    """Raised when all retry attempts fail."""
    
    def __init__(self, message: str, last_error: Exception, attempts: int):
        super().__init__(message)
        self.last_error = last_error
        self.attempts = attempts


async def retry_async(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> T:
    """Retry async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for delay between attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between attempts
        exceptions: Tuple of exceptions to catch and retry
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of the function call
        
    Raises:
        RetryError: When all attempts fail
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_error = e
            if attempt == max_attempts - 1:
                raise RetryError(
                    f"Failed after {max_attempts} attempts",
                    last_error=e,
                    attempts=max_attempts
                )
            
            delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
            await asyncio.sleep(delay)
    
    # This should never be reached
    raise RetryError(
        f"Failed after {max_attempts} attempts",
        last_error=last_error,
        attempts=max_attempts
    )


def retry_sync(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> T:
    """Retry synchronous function with exponential backoff.
    
    Args:
        func: Function to retry
        *args: Positional arguments for func
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for delay between attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between attempts
        exceptions: Tuple of exceptions to catch and retry
        **kwargs: Keyword arguments for func
        
    Returns:
        Result of the function call
        
    Raises:
        RetryError: When all attempts fail
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_error = e
            if attempt == max_attempts - 1:
                raise RetryError(
                    f"Failed after {max_attempts} attempts",
                    last_error=e,
                    attempts=max_attempts
                )
            
            delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
            time.sleep(delay)
    
    # This should never be reached
    raise RetryError(
        f"Failed after {max_attempts} attempts",
        last_error=last_error,
        attempts=max_attempts
    )


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for adding retry logic to functions.
    
    Works with both sync and async functions.
    
    Args:
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for delay between attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between attempts
        exceptions: Tuple of exceptions to catch and retry
        
    Example:
        @with_retry(max_attempts=5, exceptions=(ConnectionError,))
        async def fetch_data():
            # May raise ConnectionError
            return await api_call()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_async(
                    func, *args,
                    max_attempts=max_attempts,
                    backoff_factor=backoff_factor,
                    initial_delay=initial_delay,
                    max_delay=max_delay,
                    exceptions=exceptions,
                    **kwargs
                )
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_sync(
                    func, *args,
                    max_attempts=max_attempts,
                    backoff_factor=backoff_factor,
                    initial_delay=initial_delay,
                    max_delay=max_delay,
                    exceptions=exceptions,
                    **kwargs
                )
            return sync_wrapper
    
    return decorator