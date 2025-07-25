"""
Settings configuration for Refold Helper Bot.
Handles environment variables and runtime configuration.
"""

import os
import argparse
from typing import Optional, Dict


class Settings:
    """Centralized settings management with environment variable support."""
    
    def __init__(self):
        # Parse command line arguments for backward compatibility
        parser = argparse.ArgumentParser(description='Refold Helper Bot')
        parser.add_argument('auth_key', type=str, nargs='?', 
                          help='Discord bot token (can also use BOT_TOKEN env var)')
        args, _ = parser.parse_known_args()
        
        # Bot authentication
        self.BOT_TOKEN = args.auth_key or os.getenv('BOT_TOKEN')
        if not self.BOT_TOKEN:
            raise ValueError("Bot token must be provided via command line or BOT_TOKEN environment variable")
        
        # Server configuration
        self.MAIN_SERVER_ID = int(os.getenv('MAIN_SERVER_ID', '775877387426332682'))
        
        # Logging configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.LOG_DIR = os.getenv('LOG_DIR', './logs')
        self.LOG_FILE = os.getenv('LOG_FILE', 'refold_bot.log')
        self.LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', str(10 * 1024 * 1024)))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # Monitoring configuration
        self.PERFORMANCE_MONITORING_ENABLED = os.getenv('PERFORMANCE_MONITORING_ENABLED', 'true').lower() == 'true'
        self.HEALTH_CHECKS_ENABLED = os.getenv('HEALTH_CHECKS_ENABLED', 'true').lower() == 'true'
        self.HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '300'))  # 5 minutes
        
        # Alert configuration
        self.ALERTS_ENABLED = os.getenv('ALERTS_ENABLED', 'false').lower() == 'true'
        self.ALERT_WEBHOOK_GENERAL = os.getenv('ALERT_WEBHOOK_GENERAL')
        self.ALERT_WEBHOOK_ERRORS = os.getenv('ALERT_WEBHOOK_ERRORS')
        self.ALERT_WEBHOOK_PERFORMANCE = os.getenv('ALERT_WEBHOOK_PERFORMANCE')
        self.ALERT_WEBHOOK_HEALTH = os.getenv('ALERT_WEBHOOK_HEALTH')
        self.ALERT_RATE_LIMIT_COUNT = int(os.getenv('ALERT_RATE_LIMIT_COUNT', '5'))
        self.ALERT_RATE_LIMIT_MINUTES = int(os.getenv('ALERT_RATE_LIMIT_MINUTES', '10'))
        
        # Environment configuration
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').lower()
        self.DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Timezone configuration
        self.TIMEZONE = os.getenv('TIMEZONE', 'America/Los_Angeles')
        
        # Scheduling configuration
        self.DAILY_THREAD_HOUR = int(os.getenv('DAILY_THREAD_HOUR', '16'))
        self.DAILY_THREAD_MINUTE = int(os.getenv('DAILY_THREAD_MINUTE', '0'))
        self.WEEKLY_THREAD_HOUR = int(os.getenv('WEEKLY_THREAD_HOUR', '9'))
        self.WEEKLY_THREAD_MINUTE = int(os.getenv('WEEKLY_THREAD_MINUTE', '0'))
        self.WEEKLY_THREAD_DAY = int(os.getenv('WEEKLY_THREAD_DAY', '4'))  # Friday
        
        # Data storage configuration
        self.DATA_DIR = os.getenv('DATA_DIR', './data')
        
        # Command prefix
        self.COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')
        
        # Performance thresholds
        self.SLOW_COMMAND_THRESHOLD_MS = int(os.getenv('SLOW_COMMAND_THRESHOLD_MS', '1000'))
        self.SLOW_OPERATION_THRESHOLD_MS = int(os.getenv('SLOW_OPERATION_THRESHOLD_MS', '500'))
        
        # Error handling configuration
        self.ERROR_RECOVERY_ENABLED = os.getenv('ERROR_RECOVERY_ENABLED', 'true').lower() == 'true'
        self.MAX_ERROR_RETRIES = int(os.getenv('MAX_ERROR_RETRIES', '3'))
        self.ERROR_RETRY_DELAY_SECONDS = int(os.getenv('ERROR_RETRY_DELAY_SECONDS', '5'))
    
    def validate(self) -> None:
        """Validate that all required settings are present and valid."""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if self.DAILY_THREAD_HOUR < 0 or self.DAILY_THREAD_HOUR > 23:
            raise ValueError("DAILY_THREAD_HOUR must be between 0 and 23")
        
        if self.WEEKLY_THREAD_DAY < 0 or self.WEEKLY_THREAD_DAY > 6:
            raise ValueError("WEEKLY_THREAD_DAY must be between 0 and 6")
        
        if self.LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError("LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        
        if self.ENVIRONMENT not in ['development', 'staging', 'production']:
            print(f"Warning: Unknown environment '{self.ENVIRONMENT}', expected development/staging/production")
    
    def get_alert_webhooks(self) -> Dict[str, str]:
        """Get configured alert webhooks."""
        webhooks = {}
        
        if self.ALERT_WEBHOOK_GENERAL:
            webhooks['general'] = self.ALERT_WEBHOOK_GENERAL
        if self.ALERT_WEBHOOK_ERRORS:
            webhooks['errors'] = self.ALERT_WEBHOOK_ERRORS
        if self.ALERT_WEBHOOK_PERFORMANCE:
            webhooks['performance'] = self.ALERT_WEBHOOK_PERFORMANCE
        if self.ALERT_WEBHOOK_HEALTH:
            webhooks['health'] = self.ALERT_WEBHOOK_HEALTH
        
        return webhooks
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == 'development'
    
    def get_log_config(self) -> Dict[str, any]:
        """Get logging configuration dictionary."""
        return {
            'level': self.LOG_LEVEL,
            'log_dir': self.LOG_DIR,
            'log_file': self.LOG_FILE,
            'max_file_size': self.LOG_MAX_SIZE,
            'backup_count': self.LOG_BACKUP_COUNT
        }
    
    def get_monitoring_config(self) -> Dict[str, any]:
        """Get monitoring configuration dictionary."""
        return {
            'performance_enabled': self.PERFORMANCE_MONITORING_ENABLED,
            'health_checks_enabled': self.HEALTH_CHECKS_ENABLED,
            'health_check_interval': self.HEALTH_CHECK_INTERVAL,
            'slow_command_threshold': self.SLOW_COMMAND_THRESHOLD_MS,
            'slow_operation_threshold': self.SLOW_OPERATION_THRESHOLD_MS
        }
    
    def get_alert_config(self) -> Dict[str, any]:
        """Get alert configuration dictionary."""
        return {
            'enabled': self.ALERTS_ENABLED,
            'webhooks': self.get_alert_webhooks(),
            'rate_limit_count': self.ALERT_RATE_LIMIT_COUNT,
            'rate_limit_minutes': self.ALERT_RATE_LIMIT_MINUTES
        }


# Global settings instance
settings = Settings()