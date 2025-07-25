"""
Logging system for Refold Helper Bot.
Provides structured logging with multiple outputs and professional formatting.
"""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from log record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for console output."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability."""
        # Add color for console output
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green  
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset = '\033[0m'
        
        formatted = super().format(record)
        
        # Add color if outputting to terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = colors.get(record.levelname, '')
            formatted = f"{color}{formatted}{reset}"
        
        return formatted


class BotLogger:
    """Enhanced logger with bot-specific functionality."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        # Removed _setup_done and _ensure_setup() to prevent recursion
        # setup_logging() should be called explicitly before creating loggers
    
    def debug(self, message: str, **kwargs):
        """Log debug message with extra context."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with extra context."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with extra context."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with extra context."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with extra context."""
        self.logger.critical(message, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback and extra context."""
        self.logger.exception(message, extra=kwargs)
    
    def command_start(self, command_name: str, user_id: int, guild_id: Optional[int] = None, **kwargs):
        """Log command execution start."""
        self.info(
            f"command_started",
            command_name=command_name,
            user_id=user_id,
            guild_id=guild_id,
            **kwargs
        )
    
    def command_success(self, command_name: str, duration_ms: float, **kwargs):
        """Log successful command completion."""
        self.info(
            f"command_completed",
            command_name=command_name,
            duration_ms=duration_ms,
            status="success",
            **kwargs
        )
    
    def command_error(self, command_name: str, error: str, duration_ms: float, **kwargs):
        """Log command error."""
        self.error(
            f"command_failed",
            command_name=command_name,
            error=error,
            duration_ms=duration_ms,
            status="error",
            **kwargs
        )
    
    def data_operation(self, operation: str, data_type: str, success: bool, **kwargs):
        """Log data operation."""
        level_func = self.info if success else self.error
        level_func(
            f"data_operation",
            operation=operation,
            data_type=data_type,
            success=success,
            **kwargs
        )
    
    def discord_event(self, event_name: str, **kwargs):
        """Log Discord event."""
        self.info(
            f"discord_event",
            event_name=event_name,
            **kwargs
        )
    
    def service_operation(self, service_name: str, operation: str, success: bool, **kwargs):
        """Log service operation."""
        level_func = self.info if success else self.error
        level_func(
            f"service_operation",
            service_name=service_name,
            operation=operation,
            success=success,
            **kwargs
        )


# Global flag to prevent multiple setup calls
_logging_setup_done = False


def setup_logging(
    level: str = None,
    log_file: str = None,
    log_dir: str = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    Setup logging configuration for the bot.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log file name
        log_dir: Directory for log files
        max_file_size: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    global _logging_setup_done
    
    # Prevent multiple setup calls
    if _logging_setup_done:
        return
    
    # Use settings or defaults
    level = level or getattr(settings, 'LOG_LEVEL', 'INFO')
    log_dir = log_dir or getattr(settings, 'LOG_DIR', './logs')
    log_file = log_file or 'refold_bot.log'
    
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with human-readable format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(HumanFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler with structured JSON format
    file_path = log_path / log_file
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # File gets everything
    file_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    # Discord.py can be very verbose, reduce its level
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    
    # Aiohttp can also be verbose
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    # Mark setup as complete
    _logging_setup_done = True
    
    # Log startup message using basic logger (not BotLogger to avoid recursion)
    startup_logger = logging.getLogger('bot.startup')
    startup_logger.info(f"Logging initialized - level: {level}, file: {file_path}")


def get_logger(name: str) -> BotLogger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name (usually module name)
        
    Returns:
        BotLogger instance
    """
    return BotLogger(name)


def log_performance(operation: str, duration_ms: float, **kwargs):
    """
    Log performance metrics for an operation.
    
    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        **kwargs: Additional context
    """
    perf_logger = get_logger('bot.performance')
    
    # Determine if this is slow
    slow_threshold = 1000  # 1 second
    is_slow = duration_ms > slow_threshold
    
    level_func = perf_logger.warning if is_slow else perf_logger.info
    level_func(
        "performance_metric",
        operation=operation,
        duration_ms=duration_ms,
        is_slow=is_slow,
        **kwargs
    )


def log_health_check(check_name: str, healthy: bool, **kwargs):
    """
    Log health check results.
    
    Args:
        check_name: Name of the health check
        healthy: Whether the check passed
        **kwargs: Additional context
    """
    health_logger = get_logger('bot.health')
    level_func = health_logger.info if healthy else health_logger.error
    level_func(
        "health_check",
        check_name=check_name,
        healthy=healthy,
        **kwargs
    )