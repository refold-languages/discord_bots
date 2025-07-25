"""
Alert system for Refold Helper Bot.
Provides critical error notifications and health alerts via Discord webhooks.
"""

import asyncio
import aiohttp
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from enum import Enum

from .logger import get_logger
from .error_handler import BotError
from .monitoring import HealthCheckResult


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert destination channels."""
    GENERAL = "general"
    ERRORS = "errors"
    PERFORMANCE = "performance"
    HEALTH = "health"


class Alert:
    """Data class for alerts."""
    
    def __init__(self, 
                 level: AlertLevel,
                 title: str,
                 message: str,
                 channel: AlertChannel = AlertChannel.GENERAL,
                 **context):
        self.level = level
        self.title = title
        self.message = message
        self.channel = channel
        self.context = context
        self.timestamp = datetime.utcnow()
        self.id = f"{level.value}_{hash(title + message) % 10000}_{int(self.timestamp.timestamp())}"
    
    def to_embed_data(self) -> Dict[str, Any]:
        """Convert alert to Discord embed data."""
        colors = {
            AlertLevel.INFO: 0x3498db,      # Blue
            AlertLevel.WARNING: 0xf39c12,   # Orange
            AlertLevel.ERROR: 0xe74c3c,     # Red
            AlertLevel.CRITICAL: 0x8e44ad,  # Purple
        }
        
        embed_data = {
            "title": f"{self.level.value.upper()}: {self.title}",
            "description": self.message,
            "color": colors.get(self.level, 0x95a5a6),
            "timestamp": self.timestamp.isoformat(),
            "fields": []
        }
        
        # Add context fields
        for key, value in self.context.items():
            if value is not None and str(value).strip():
                embed_data["fields"].append({
                    "name": key.replace("_", " ").title(),
                    "value": str(value)[:1024],  # Discord field value limit
                    "inline": True
                })
        
        # Add footer
        embed_data["footer"] = {
            "text": f"Alert ID: {self.id}"
        }
        
        return embed_data


class RateLimiter:
    """Rate limiter for alerts to prevent spam."""
    
    def __init__(self, max_alerts: int = 5, time_window_minutes: int = 10):
        self.max_alerts = max_alerts
        self.time_window = timedelta(minutes=time_window_minutes)
        self.alert_history: Dict[str, List[datetime]] = defaultdict(list)
    
    def is_allowed(self, alert_key: str) -> bool:
        """Check if an alert is allowed based on rate limiting."""
        now = datetime.utcnow()
        cutoff = now - self.time_window
        
        # Clean old alerts
        self.alert_history[alert_key] = [
            timestamp for timestamp in self.alert_history[alert_key]
            if timestamp > cutoff
        ]
        
        # Check if we're under the limit
        if len(self.alert_history[alert_key]) < self.max_alerts:
            self.alert_history[alert_key].append(now)
            return True
        
        return False
    
    def get_next_allowed_time(self, alert_key: str) -> Optional[datetime]:
        """Get when the next alert of this type will be allowed."""
        if alert_key not in self.alert_history:
            return None
        
        oldest_alert = min(self.alert_history[alert_key])
        return oldest_alert + self.time_window


class AlertSystem:
    """Main alert system for sending notifications."""
    
    def __init__(self):
        self.logger = get_logger('bot.alerts')
        self.webhook_urls: Dict[AlertChannel, str] = {}
        self.rate_limiter = RateLimiter()
        self.enabled = True
        self.session: Optional[aiohttp.ClientSession] = None
    
    def configure_webhook(self, channel: AlertChannel, webhook_url: str):
        """Configure webhook URL for an alert channel."""
        self.webhook_urls[channel] = webhook_url
        self.logger.info("webhook_configured", channel=channel.value)
    
    def configure_webhooks(self, webhook_config: Dict[str, str]):
        """Configure multiple webhooks from a dictionary."""
        for channel_name, url in webhook_config.items():
            try:
                channel = AlertChannel(channel_name.lower())
                self.configure_webhook(channel, url)
            except ValueError:
                self.logger.warning("invalid_alert_channel", channel=channel_name)
    
    def enable(self):
        """Enable alert sending."""
        self.enabled = True
        self.logger.info("alert_system_enabled")
    
    def disable(self):
        """Disable alert sending."""
        self.enabled = False
        self.logger.info("alert_system_disabled")
    
    async def send_alert(self, alert: Alert, bypass_rate_limit: bool = False) -> bool:
        """
        Send an alert via webhook.
        
        Args:
            alert: Alert to send
            bypass_rate_limit: Skip rate limiting for critical alerts
            
        Returns:
            True if alert was sent successfully
        """
        if not self.enabled:
            self.logger.debug("alert_skipped_disabled", alert_id=alert.id)
            return False
        
        # Check rate limiting
        alert_key = f"{alert.channel.value}:{alert.level.value}:{hash(alert.title) % 1000}"
        if not bypass_rate_limit and not self.rate_limiter.is_allowed(alert_key):
            self.logger.warning("alert_rate_limited", 
                              alert_key=alert_key, 
                              alert_id=alert.id,
                              next_allowed=self.rate_limiter.get_next_allowed_time(alert_key))
            return False
        
        # Get webhook URL for channel
        webhook_url = self.webhook_urls.get(alert.channel)
        if not webhook_url:
            self.logger.error("no_webhook_configured", 
                            channel=alert.channel.value,
                            alert_id=alert.id)
            return False
        
        # Send the alert
        try:
            success = await self._send_webhook(webhook_url, alert)
            if success:
                self.logger.info("alert_sent_successfully", 
                               alert_id=alert.id,
                               channel=alert.channel.value,
                               level=alert.level.value)
            return success
            
        except Exception as e:
            self.logger.error("alert_send_failed",
                            alert_id=alert.id,
                            error=str(e),
                            webhook_url=webhook_url[:50] + "...")
            return False
    
    async def _send_webhook(self, webhook_url: str, alert: Alert) -> bool:
        """Send webhook HTTP request."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        embed_data = alert.to_embed_data()
        payload = {
            "embeds": [embed_data],
            "username": "Refold Bot Alerts"
        }
        
        try:
            async with self.session.post(webhook_url, json=payload) as response:
                if response.status == 204:  # Discord webhook success
                    return True
                else:
                    self.logger.error("webhook_bad_response",
                                    status=response.status,
                                    response_text=await response.text())
                    return False
                    
        except asyncio.TimeoutError:
            self.logger.error("webhook_timeout", webhook_url=webhook_url[:50] + "...")
            return False
        except Exception as e:
            self.logger.error("webhook_request_failed", error=str(e))
            return False
    
    async def send_error_alert(self, error: BotError, **extra_context) -> bool:
        """Send an alert for a bot error."""
        level = AlertLevel.CRITICAL if not error.recoverable else AlertLevel.ERROR
        
        alert = Alert(
            level=level,
            title=f"{error.__class__.__name__} Occurred",
            message=error.message,
            channel=AlertChannel.ERRORS,
            error_type=error.__class__.__name__,
            recoverable=error.recoverable,
            user_message=error.user_message,
            **error.context,
            **extra_context
        )
        
        return await self.send_alert(alert, bypass_rate_limit=(level == AlertLevel.CRITICAL))
    
    async def send_health_alert(self, health_result: HealthCheckResult) -> bool:
        """Send an alert for a failed health check."""
        if health_result.healthy:
            return True  # No alert needed for healthy checks
        
        alert = Alert(
            level=AlertLevel.ERROR,
            title=f"Health Check Failed: {health_result.name}",
            message=health_result.message,
            channel=AlertChannel.HEALTH,
            check_name=health_result.name,
            duration_ms=health_result.duration_ms,
            **health_result.context
        )
        
        return await self.send_alert(alert)
    
    async def send_performance_alert(self, operation: str, duration_ms: float, **context) -> bool:
        """Send an alert for slow performance."""
        alert = Alert(
            level=AlertLevel.WARNING,
            title=f"Slow Performance Detected",
            message=f"Operation '{operation}' took {duration_ms:.1f}ms",
            channel=AlertChannel.PERFORMANCE,
            operation=operation,
            duration_ms=duration_ms,
            **context
        )
        
        return await self.send_alert(alert)
    
    async def send_info_alert(self, title: str, message: str, **context) -> bool:
        """Send an informational alert."""
        alert = Alert(
            level=AlertLevel.INFO,
            title=title,
            message=message,
            channel=AlertChannel.GENERAL,
            **context
        )
        
        return await self.send_alert(alert)
    
    async def send_critical_alert(self, title: str, message: str, **context) -> bool:
        """Send a critical alert that bypasses rate limiting."""
        alert = Alert(
            level=AlertLevel.CRITICAL,
            title=title,
            message=message,
            channel=AlertChannel.ERRORS,
            **context
        )
        
        return await self.send_alert(alert, bypass_rate_limit=True)
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status."""
        status = {}
        for alert_key, timestamps in self.rate_limiter.alert_history.items():
            next_allowed = self.rate_limiter.get_next_allowed_time(alert_key)
            status[alert_key] = {
                'recent_count': len(timestamps),
                'max_allowed': self.rate_limiter.max_alerts,
                'next_allowed': next_allowed.isoformat() if next_allowed else None,
                'is_rate_limited': len(timestamps) >= self.rate_limiter.max_alerts
            }
        return status
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None


# Global alert system instance
alert_system = AlertSystem()


async def send_startup_alert():
    """Send alert when bot starts up."""
    await alert_system.send_info_alert(
        "Bot Startup",
        "Refold Helper Bot has started successfully",
        timestamp=datetime.utcnow().isoformat()
    )


async def send_shutdown_alert():
    """Send alert when bot shuts down."""
    await alert_system.send_info_alert(
        "Bot Shutdown", 
        "Refold Helper Bot is shutting down",
        timestamp=datetime.utcnow().isoformat()
    )