"""
Error handling framework for Refold Helper Bot.
Provides custom exceptions, error recovery, and user-friendly error responses.
"""

import traceback
from typing import Optional, Dict, Any, Callable
from datetime import datetime

import discord
from discord.ext import commands

from .logger import get_logger


class BotError(Exception):
    """Base exception for all bot-related errors."""
    
    def __init__(self, message: str, user_message: str = None, recoverable: bool = True, **context):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "Something went wrong. Please try again."
        self.recoverable = recoverable
        # Filter out any user_message from context to avoid conflicts
        self.context = {k: v for k, v in context.items() if k != 'user_message'}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'user_message': self.user_message,
            'recoverable': self.recoverable,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context
        }


class ValidationError(BotError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: str = None, value: Any = None, **context):
        user_msg = f"Invalid input provided. Please check your {field or 'data'} and try again."
        # Remove user_message from context to avoid conflicts
        clean_context = {k: v for k, v in context.items() if k != 'user_message'}
        super().__init__(message, user_message=user_msg, recoverable=True, field=field, value=value, **clean_context)


class DataError(BotError):
    """Raised when data operations fail."""
    
    def __init__(self, message: str, operation: str = None, data_type: str = None, **context):
        user_msg = "There was a problem accessing the data. Please try again in a moment."
        # Remove user_message from context to avoid conflicts
        clean_context = {k: v for k, v in context.items() if k != 'user_message'}
        super().__init__(message, user_message=user_msg, recoverable=True, operation=operation, data_type=data_type, **clean_context)


class DiscordError(BotError):
    """Raised when Discord API operations fail."""
    
    def __init__(self, message: str, discord_error: discord.DiscordException = None, **context):
        # Determine user message based on Discord error type
        user_msg = self._get_user_message(discord_error)
        recoverable = self._is_recoverable(discord_error)
        
        # Remove user_message from context to avoid conflicts
        clean_context = {k: v for k, v in context.items() if k != 'user_message'}
        super().__init__(message, user_message=user_msg, recoverable=recoverable, discord_error=str(discord_error), **clean_context)
        self.discord_error = discord_error
    
    def _get_user_message(self, discord_error: Optional[discord.DiscordException]) -> str:
        """Get user-friendly message based on Discord error type."""
        if isinstance(discord_error, discord.Forbidden):
            return "I don't have permission to do that. Please check my role permissions."
        elif isinstance(discord_error, discord.NotFound):
            return "The requested resource was not found. It may have been deleted."
        elif isinstance(discord_error, discord.HTTPException):
            if discord_error.status == 429:  # Rate limited
                return "I'm being rate limited. Please try again in a moment."
            else:
                return "Discord is experiencing issues. Please try again later."
        else:
            return "There was a problem communicating with Discord. Please try again."
    
    def _is_recoverable(self, discord_error: Optional[discord.DiscordException]) -> bool:
        """Determine if the Discord error is recoverable."""
        if isinstance(discord_error, (discord.HTTPException, discord.ConnectionClosed)):
            return True
        elif isinstance(discord_error, discord.Forbidden):
            return False  # Permission errors usually require manual intervention
        else:
            return True


class ServiceError(BotError):
    """Raised when service operations fail."""
    
    def __init__(self, message: str, service_name: str = None, operation: str = None, **context):
        user_msg = f"The {service_name or 'service'} is temporarily unavailable. Please try again later."
        # Remove user_message from context to avoid conflicts
        clean_context = {k: v for k, v in context.items() if k != 'user_message'}
        super().__init__(message, user_message=user_msg, recoverable=True, service_name=service_name, operation=operation, **clean_context)


class ConfigurationError(BotError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: str = None, **context):
        user_msg = "The bot configuration is invalid. Please contact an administrator."
        # Remove user_message from context to avoid conflicts
        clean_context = {k: v for k, v in context.items() if k != 'user_message'}
        super().__init__(message, user_message=user_msg, recoverable=False, config_key=config_key, **clean_context)


class RateLimitError(BotError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: float = None, **context):
        user_msg = f"Please slow down! Try again in {retry_after or 60} seconds."
        # Remove user_message from context to avoid conflicts
        clean_context = {k: v for k, v in context.items() if k != 'user_message'}
        super().__init__(message, user_message=user_msg, recoverable=True, retry_after=retry_after, **clean_context)


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self):
        self.logger = get_logger('bot.errors')
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[type, Callable] = {}
    
    def register_recovery_strategy(self, error_type: type, strategy: Callable):
        """Register a recovery strategy for a specific error type."""
        self.recovery_strategies[error_type] = strategy
    
    async def handle_command_error(self, ctx: commands.Context, error: Exception) -> bool:
        """
        Handle command errors with appropriate logging and user feedback.
        
        Args:
            ctx: Command context
            error: The exception that occurred
            
        Returns:
            True if error was handled, False if it should propagate
        """
        # Convert to BotError if needed
        if not isinstance(error, BotError):
            error = self._convert_to_bot_error(error)
        
        # Log the error
        self.logger.error(
            "command_error_occurred",
            command=ctx.command.name if ctx.command else "unknown",
            user_id=ctx.author.id,
            guild_id=ctx.guild.id if ctx.guild else None,
            error_data=error.to_dict()
        )
        
        # Track error frequency
        self._track_error(error)
        
        # Try recovery if strategy exists
        if type(error) in self.recovery_strategies:
            try:
                await self.recovery_strategies[type(error)](ctx, error)
                return True
            except Exception as recovery_error:
                self.logger.error(
                    "error_recovery_failed",
                    original_error=str(error),
                    recovery_error=str(recovery_error)
                )
        
        # Send user-friendly error message
        try:
            await ctx.send(f"❌ {error.user_message}")
        except discord.DiscordException as send_error:
            self.logger.error(
                "failed_to_send_error_message",
                original_error=str(error),
                send_error=str(send_error)
            )
        
        return True
    
    async def handle_event_error(self, event_name: str, error: Exception, **context) -> bool:
        """
        Handle errors that occur in event handlers.
        
        Args:
            event_name: Name of the event where error occurred
            error: The exception that occurred
            context: Additional context about the event
            
        Returns:
            True if error was handled, False if it should propagate
        """
        # Convert to BotError if needed
        if not isinstance(error, BotError):
            error = self._convert_to_bot_error(error)
        
        # Log the error
        self.logger.error(
            "event_error_occurred",
            event_name=event_name,
            error_data=error.to_dict(),
            **context
        )
        
        # Track error frequency
        self._track_error(error)
        
        # Events should generally not crash the bot
        return True
    
    def _convert_to_bot_error(self, error: Exception) -> BotError:
        """Convert standard exceptions to BotError instances."""
        if isinstance(error, commands.CommandError):
            return self._convert_command_error(error)
        elif isinstance(error, discord.DiscordException):
            return DiscordError("Discord API error occurred", discord_error=error)
        elif isinstance(error, (ValueError, TypeError)):
            return ValidationError(str(error))
        elif isinstance(error, (FileNotFoundError, PermissionError, OSError)):
            return DataError(str(error))
        else:
            return BotError(
                str(error),
                user_message="An unexpected error occurred. Please try again.",
                recoverable=True
            )
    
    def _convert_command_error(self, error: commands.CommandError) -> BotError:
        """Convert discord.py command errors to BotError instances."""
        if isinstance(error, commands.MissingPermissions):
            return BotError(
                str(error),
                user_message="You don't have permission to use this command.",
                recoverable=False
            )
        elif isinstance(error, commands.BotMissingPermissions):
            return BotError(
                str(error),
                user_message="I don't have the required permissions to run this command.",
                recoverable=False
            )
        elif isinstance(error, commands.CommandNotFound):
            return BotError(
                str(error),
                user_message="Command not found. Use `!help` to see available commands.",
                recoverable=False
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            return ValidationError(
                str(error),
                user_message=f"Missing required argument: {error.param.name}",
                field=error.param.name
            )
        elif isinstance(error, commands.BadArgument):
            return ValidationError(
                str(error),
                user_message="Invalid argument provided. Please check your input."
            )
        elif isinstance(error, commands.CommandOnCooldown):
            return RateLimitError(
                str(error),
                user_message=f"Command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                retry_after=error.retry_after
            )
        else:
            return BotError(str(error))
    
    def _track_error(self, error: BotError):
        """Track error frequency for monitoring."""
        error_key = f"{error.__class__.__name__}:{hash(error.message) % 1000}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log if error is becoming frequent
        if self.error_counts[error_key] % 10 == 0:
            self.logger.warning(
                "frequent_error_detected",
                error_key=error_key,
                count=self.error_counts[error_key],
                error_type=error.__class__.__name__
            )
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get current error statistics."""
        return self.error_counts.copy()
    
    def reset_error_stats(self):
        """Reset error statistics."""
        self.error_counts.clear()


# Global error handler instance
error_handler = ErrorHandler()


async def handle_error(ctx_or_event: str, error: Exception, **context) -> bool:
    """
    Convenience function for handling errors.
    
    Args:
        ctx_or_event: Command context or event name
        error: Exception that occurred
        context: Additional context
        
    Returns:
        True if error was handled
    """
    if isinstance(ctx_or_event, commands.Context):
        return await error_handler.handle_command_error(ctx_or_event, error)
    else:
        return await error_handler.handle_event_error(ctx_or_event, error, **context)


def safe_execute(operation_name: str):
    """
    Decorator for safe execution of operations with error handling.
    
    Args:
        operation_name: Name of the operation for logging
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = get_logger(f'bot.safe_execute.{operation_name}')
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"{operation_name}_completed", success=True)
                return result
            except Exception as e:
                logger.error(
                    f"{operation_name}_failed",
                    error=str(e),
                    error_type=type(e).__name__
                )
                # Re-raise as BotError if not already one
                if not isinstance(e, BotError):
                    raise ServiceError(f"{operation_name} failed: {str(e)}", operation=operation_name) from e
                raise
        return wrapper
    return decorator