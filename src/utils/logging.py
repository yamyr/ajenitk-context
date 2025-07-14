"""Logging configuration and utilities.

This module provides centralized logging setup and configuration for
the Ajentik application.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for terminal output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add color to level name
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        # Format the message
        formatted = super().format(record)
        
        # Reset level name
        record.levelname = record.levelname.replace(self.COLORS.get(record.levelname, ''), '').replace(self.RESET, '')
        
        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'msecs', 'levelname',
                          'levelno', 'pathname', 'filename', 'module', 'funcName',
                          'lineno', 'exc_info', 'exc_text', 'stack_info', 'message']:
                log_obj[key] = value
        
        return json.dumps(log_obj)


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    json_format: bool = False,
    disable_colors: bool = False
) -> None:
    """Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Use JSON formatting for logs
        disable_colors: Disable colored output
    """
    # Determine log level
    if level is None:
        level = 'INFO'
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatters
    if json_format:
        formatter = JSONFormatter()
    elif disable_colors:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            JSONFormatter() if json_format else logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        root_logger.addHandler(file_handler)
    
    # Set levels for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding context to log messages."""
    
    def __init__(self, logger: logging.Logger, **kwargs):
        """Initialize log context.
        
        Args:
            logger: Logger instance
            **kwargs: Context values to add to logs
        """
        self.logger = logger
        self.context = kwargs
        self.old_factory = None
    
    def __enter__(self):
        """Enter context."""
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        self.old_factory = old_factory
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


def log_execution_time(logger: logging.Logger):
    """Decorator to log function execution time.
    
    Args:
        logger: Logger instance to use
        
    Example:
        @log_execution_time(logger)
        def slow_function():
            time.sleep(1)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            try:
                result = func(*args, **kwargs)
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(
                    f"{func.__name__} completed in {elapsed:.3f}s",
                    extra={'execution_time': elapsed, 'function': func.__name__}
                )
                return result
            except Exception as e:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.error(
                    f"{func.__name__} failed after {elapsed:.3f}s: {str(e)}",
                    extra={'execution_time': elapsed, 'function': func.__name__}
                )
                raise
        
        return wrapper
    return decorator