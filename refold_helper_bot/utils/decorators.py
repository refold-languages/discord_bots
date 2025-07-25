"""
Command decorators and utilities for Refold Helper Bot.
Provides easy-to-use decorators for performance monitoring, error handling, and logging.
"""

import functools
import time
from typing import Callable, Any

from discord.ext import commands

from .logger import get_logger
from .monitoring import performance_monitor
from .error_handler import handle_error
from .alerts import alert_system
from config.settings import settings


def monitor_command(
    log_execution: bool = True,
    track_performance: bool = True,
    alert_on_slow: bool = True,
    alert_threshold_ms: int = None
):
    """
    Comprehensive command monitoring decorator.
    
    Args:
        log_execution: Whether to log command execution details
        track_performance: Whether to track performance metrics
        alert_on_slow: Whether to send alerts for slow commands
        alert_threshold_ms: Custom threshold for slow command alerts
        
    Usage:
        @commands.command()
        @monitor_command()
        async def mycommand(self, ctx):
            # Command implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs) -> Any:
            # Get logger from the cog instance or create one
            logger = getattr(self, 'logger', None) or get_logger(f'command.{func.__name__}')
            
            start_time = time.perf_counter()
            command_name = ctx.command.name if ctx.command else func.__name__
            
            # Log command start
            if log_execution:
                logger.command_start(
                    command_name,
                    ctx.author.id,
                    ctx.guild.id if ctx.guild else None,
                    channel_id=ctx.channel.id
                )
            
            try:
                # Track performance if enabled
                if track_performance:
                    async with performance_monitor.track(
                        f"command_{command_name}",
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id if ctx.guild else None,
                        channel_id=ctx.channel.id
                    ):
                        result = await func(self, ctx, *args, **kwargs)
                else:
                    result = await func(self, ctx, *args, **kwargs)
                
                # Calculate duration and log success
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                if log_execution:
                    logger.command_success(command_name, duration_ms)
                
                # Check for slow commands and alert if needed
                threshold = alert_threshold_ms or settings.SLOW_COMMAND_THRESHOLD_MS
                if alert_on_slow and duration_ms > threshold:
                    logger.warning("slow_command_detected",
                                 command_name=command_name,
                                 duration_ms=duration_ms,
                                 threshold_ms=threshold,
                                 user_id=ctx.author.id)
                    
                    if settings.ALERTS_ENABLED:
                        await alert_system.send_performance_alert(
                            f"command_{command_name}",
                            duration_ms,
                            user_id=ctx.author.id,
                            guild_id=ctx.guild.id if ctx.guild else None,
                            threshold_ms=threshold
                        )
                
                return result
                
            except Exception as e:
                # Calculate duration and log error
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                if log_execution:
                    logger.command_error(command_name, str(e), duration_ms)
                
                # Let the error handler deal with it
                await handle_error(ctx, e)
                
        return wrapper
    return decorator


def admin_only(func: Callable) -> Callable:
    """
    Decorator to restrict command to administrators with proper logging.
    
    Usage:
        @commands.command()
        @admin_only
        async def admincommand(self, ctx):
            # Admin-only command implementation
            pass
    """
    @functools.wraps(func)
    async def wrapper(self, ctx: commands.Context, *args, **kwargs):
        logger = getattr(self, 'logger', None) or get_logger(f'command.{func.__name__}')
        
        if not ctx.author.guild_permissions.administrator:
            logger.warning("unauthorized_admin_command_attempt",
                         command_name=ctx.command.name if ctx.command else func.__name__,
                         user_id=ctx.author.id,
                         guild_id=ctx.guild.id if ctx.guild else None)
            
            await ctx.send("❌ You need administrator permissions to use this command.")
            return
        
        logger.info("admin_command_authorized",
                   command_name=ctx.command.name if ctx.command else func.__name__,
                   user_id=ctx.author.id,
                   guild_id=ctx.guild.id if ctx.guild else None)
        
        return await func(self, ctx, *args, **kwargs)
    
    return wrapper


def require_guild(func: Callable) -> Callable:
    """
    Decorator to ensure command is only used in guilds (not DMs).
    
    Usage:
        @commands.command()
        @require_guild
        async def guildcommand(self, ctx):
            # Guild-only command implementation
            pass
    """
    @functools.wraps(func)
    async def wrapper(self, ctx: commands.Context, *args, **kwargs):
        logger = getattr(self, 'logger', None) or get_logger(f'command.{func.__name__}')
        
        if ctx.guild is None:
            logger.info("dm_command_rejected",
                       command_name=ctx.command.name if ctx.command else func.__name__,
                       user_id=ctx.author.id)
            
            await ctx.send("❌ This command can only be used in servers, not in DMs.")
            return
        
        return await func(self, ctx, *args, **kwargs)
    
    return wrapper


def log_service_operation(operation_name: str):
    """
    Decorator for logging service operations with performance tracking.
    
    Args:
        operation_name: Name of the operation for logging
        
    Usage:
        @log_service_operation("create_project")
        async def create_project(self, name, leader, description):
            # Service operation implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            logger = getattr(self, 'logger', None) or get_logger(f'service.{operation_name}')
            
            logger.debug(f"{operation_name}_started", args_count=len(args), kwargs_keys=list(kwargs.keys()))
            
            try:
                async with performance_monitor.track(operation_name):
                    result = await func(self, *args, **kwargs)
                
                logger.info(f"{operation_name}_completed", success=True)
                return result
                
            except Exception as e:
                logger.error(f"{operation_name}_failed",
                           error=str(e),
                           error_type=type(e).__name__)
                raise
                
        return wrapper
    return decorator


def validate_args(**validators):
    """
    Decorator for argument validation with comprehensive error messages.
    
    Args:
        **validators: Dictionary of argument_name -> validation_function
        
    Usage:
        @validate_args(name=lambda x: len(x) > 0, count=lambda x: x > 0)
        async def command_with_validation(self, ctx, name: str, count: int):
            # Command implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            logger = getattr(self, 'logger', None) or get_logger(f'command.{func.__name__}')
            
            # Get function signature to map args to parameter names
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(self, ctx, *args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each specified argument
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    try:
                        if not validator(value):
                            logger.warning("argument_validation_failed",
                                         command_name=ctx.command.name if ctx.command else func.__name__,
                                         parameter=param_name,
                                         value=str(value)[:100])
                            
                            await ctx.send(f"❌ Invalid value for {param_name}: {value}")
                            return
                    except Exception as e:
                        logger.error("argument_validator_error",
                                   command_name=ctx.command.name if ctx.command else func.__name__,
                                   parameter=param_name,
                                   error=str(e))
                        
                        await ctx.send(f"❌ Error validating {param_name}")
                        return
            
            return await func(self, ctx, *args, **kwargs)
        
        return wrapper
    return decorator


def rate_limit(calls: int = 5, period: int = 60):
    """
    Simple rate limiting decorator for commands.
    
    Args:
        calls: Number of calls allowed
        period: Time period in seconds
        
    Usage:
        @commands.command()
        @rate_limit(calls=3, period=30)
        async def limited_command(self, ctx):
            # Rate-limited command implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Store rate limit data on the function itself
        if not hasattr(func, '_rate_limit_data'):
            func._rate_limit_data = {}
        
        @functools.wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            logger = getattr(self, 'logger', None) or get_logger(f'command.{func.__name__}')
            
            user_id = ctx.author.id
            now = time.time()
            
            # Clean old entries
            func._rate_limit_data = {
                uid: timestamps for uid, timestamps in func._rate_limit_data.items()
                if any(ts > now - period for ts in timestamps)
            }
            
            # Check user's rate limit
            user_timestamps = func._rate_limit_data.get(user_id, [])
            recent_calls = [ts for ts in user_timestamps if ts > now - period]
            
            if len(recent_calls) >= calls:
                logger.warning("command_rate_limited",
                             command_name=ctx.command.name if ctx.command else func.__name__,
                             user_id=user_id,
                             recent_calls=len(recent_calls),
                             limit=calls)
                
                await ctx.send(f"🚫 You're doing that too often! Please wait {period} seconds between uses.")
                return
            
            # Record this call
            recent_calls.append(now)
            func._rate_limit_data[user_id] = recent_calls
            
            return await func(self, ctx, *args, **kwargs)
        
        return wrapper
    return decorator


# Convenience combinations
def monitored_admin_command(**monitor_kwargs):
    """Combination decorator for admin commands with monitoring."""
    def decorator(func: Callable) -> Callable:
        return admin_only(monitor_command(**monitor_kwargs)(func))
    return decorator


def monitored_guild_command(**monitor_kwargs):
    """Combination decorator for guild commands with monitoring."""
    def decorator(func: Callable) -> Callable:
        return require_guild(monitor_command(**monitor_kwargs)(func))
    return decorator


def safe_command(**monitor_kwargs):
    """Full-featured command decorator with all safety features."""
    def decorator(func: Callable) -> Callable:
        return require_guild(monitor_command(**monitor_kwargs)(func))
    return decorator