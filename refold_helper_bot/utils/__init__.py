"""
Utilities package for Refold Helper Bot.
Contains logging, error handling, monitoring, alert systems, and command decorators.
"""

from .logger import get_logger, setup_logging, BotLogger, log_performance, log_health_check
from .error_handler import (
    BotError, DataError, DiscordError, ValidationError, ServiceError,
    ConfigurationError, RateLimitError, handle_error, safe_execute, error_handler
)
from .monitoring import (
    PerformanceMonitor, HealthCheck, PerformanceMetric, HealthCheckResult,
    performance_monitor, health_check, create_system_health_checks
)
from .alerts import (
    AlertSystem, Alert, AlertLevel, AlertChannel, alert_system,
    send_startup_alert, send_shutdown_alert
)
from .decorators import (
    monitor_command, admin_only, require_guild, log_service_operation,
    validate_args, rate_limit, monitored_admin_command, monitored_guild_command,
    safe_command
)

__all__ = [
    # Logging
    'get_logger',
    'setup_logging',
    'BotLogger',
    'log_performance',
    'log_health_check',
    
    # Error Handling
    'BotError',
    'DataError',
    'DiscordError',
    'ValidationError',
    'ServiceError',
    'ConfigurationError',
    'RateLimitError',
    'handle_error',
    'safe_execute',
    'error_handler',
    
    # Monitoring
    'PerformanceMonitor',
    'HealthCheck',
    'PerformanceMetric',
    'HealthCheckResult',
    'performance_monitor',
    'health_check',
    'create_system_health_checks',
    
    # Alerts
    'AlertSystem',
    'Alert',
    'AlertLevel',
    'AlertChannel',
    'alert_system',
    'send_startup_alert',
    'send_shutdown_alert',
    
    # Decorators
    'monitor_command',
    'admin_only',
    'require_guild',
    'log_service_operation',
    'validate_args',
    'rate_limit',
    'monitored_admin_command',
    'monitored_guild_command',
    'safe_command',
]