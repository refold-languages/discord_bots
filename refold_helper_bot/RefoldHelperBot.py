"""
Refold Helper Bot - Main entry point
A comprehensive Discord bot for the Refold language learning community.
"""

import asyncio
import signal
import sys
import traceback
from datetime import datetime

import discord
from discord.ext import commands

# Import configuration
from config.settings import settings

# Import utilities
from utils import (
    setup_logging, get_logger, 
    error_handler, handle_error,
    performance_monitor, health_check,
    alert_system, send_startup_alert, send_shutdown_alert
)

# Import cogs
from cogs import COGS


class RefoldHelperBot(commands.Bot):
    """Main bot class with comprehensive logging, monitoring, and error handling."""
    
    def __init__(self):
        # Setup logging first
        setup_logging(**settings.get_log_config())
        self.logger = get_logger('bot.main')
        
        # Initialize Discord bot
        intents = discord.Intents.all()
        intents.members = True
        
        super().__init__(
            intents=intents, 
            command_prefix=settings.COMMAND_PREFIX
        )
        
        # Initialize monitoring and alerts
        self._setup_monitoring()
        self._setup_alerts()
        self._setup_error_handlers()
        
        # Track startup time
        self.start_time = datetime.utcnow()
        self.logger.info("bot_initializing", 
                         environment=settings.ENVIRONMENT,
                         log_level=settings.LOG_LEVEL,
                         alerts_enabled=settings.ALERTS_ENABLED)

    def _setup_monitoring(self):
        """Setup performance monitoring and health checks."""
        if settings.PERFORMANCE_MONITORING_ENABLED:
            self.logger.info("performance_monitoring_enabled")
        
        if settings.HEALTH_CHECKS_ENABLED:
            # Register bot-specific health checks
            async def discord_connection_check():
                """Check if Discord connection is healthy."""
                if self.is_closed():
                    return False, "Bot is disconnected", {}
                
                latency_ms = self.latency * 1000
                healthy = latency_ms < 1000  # Consider unhealthy if latency > 1s
                message = f"Discord latency: {latency_ms:.1f}ms"
                context = {'latency_ms': latency_ms, 'guild_count': len(self.guilds)}
                
                return healthy, message, context
            
            async def cog_health_check():
                """Check if all cogs are loaded properly."""
                loaded_cogs = len(self.cogs)
                expected_cogs = len(COGS)
                healthy = loaded_cogs == expected_cogs
                message = f"Cogs loaded: {loaded_cogs}/{expected_cogs}"
                context = {
                    'loaded_cogs': loaded_cogs,
                    'expected_cogs': expected_cogs,
                    'cog_names': list(self.cogs.keys())
                }
                
                return healthy, message, context
            
            health_check.register_check('discord_connection', discord_connection_check, 60)
            health_check.register_check('cog_health', cog_health_check, 300)
            
            self.logger.info("health_checks_enabled", 
                           interval=settings.HEALTH_CHECK_INTERVAL)

    def _setup_alerts(self):
        """Setup alert system with webhooks."""
        if settings.ALERTS_ENABLED:
            alert_system.enable()
            webhooks = settings.get_alert_webhooks()
            if webhooks:
                alert_system.configure_webhooks(webhooks)
                self.logger.info("alerts_configured", 
                               webhook_count=len(webhooks),
                               channels=list(webhooks.keys()))
            else:
                self.logger.warning("alerts_enabled_but_no_webhooks_configured")
        else:
            alert_system.disable()
            self.logger.info("alerts_disabled")

    def _setup_error_handlers(self):
        """Setup global error handling strategies."""
        async def discord_error_recovery(ctx, error):
            """Recovery strategy for Discord errors."""
            if hasattr(error, 'discord_error') and isinstance(error.discord_error, discord.HTTPException):
                # Retry after a short delay for HTTP errors
                await asyncio.sleep(2)
                self.logger.info("discord_error_recovery_attempted", 
                               command=ctx.command.name if ctx.command else "unknown")
        
        # Register recovery strategies
        from utils.error_handler import DiscordError
        error_handler.register_recovery_strategy(DiscordError, discord_error_recovery)

    async def setup_hook(self):
        """Load all cogs and start monitoring during bot setup."""
        self.logger.info("bot_setup_starting", cog_count=len(COGS))
        
        # Load cogs with performance tracking
        successful_cogs = 0
        failed_cogs = []
        
        for i, cog in enumerate(COGS):
            print(f"\n=== LOADING COG {i+1}/{len(COGS)}: {cog} ===")
            self.logger.info("attempting_to_load_cog", 
                           cog_name=cog, 
                           cog_index=i,
                           total_cogs=len(COGS))
            try:
                async with performance_monitor.track("cog_loading", cog_name=cog):
                    await self.load_extension(cog)
                    successful_cogs += 1
                    print(f"✅ SUCCESS: {cog} loaded")
                    self.logger.info("cog_loaded_successfully", cog_name=cog)
                    
                    # Log current state after each cog
                    current_cogs = list(self.cogs.keys())
                    print(f"📊 Current loaded cogs: {current_cogs}")
                    self.logger.info("current_loaded_cogs", 
                                   cog_names=current_cogs,
                                   count=len(current_cogs))
                    
            except Exception as e:
                failed_cogs.append(cog)
                print(f"❌ FAILED: {cog} - {e}")
                print(f"🔍 FULL TRACEBACK:")
                traceback.print_exc()
                print("=" * 80)
                
                self.logger.error("cog_load_failed", 
                                cog_name=cog, 
                                error=str(e),
                                error_type=type(e).__name__)
                # Log full traceback for debugging
                self.logger.error("cog_load_traceback", 
                                cog_name=cog,
                                traceback=traceback.format_exc())
        
        # Final state check
        final_cogs = list(self.cogs.keys())
        print(f"\n🏁 FINAL RESULT:")
        print(f"✅ Successful: {successful_cogs}")
        print(f"❌ Failed: {len(failed_cogs)} - {failed_cogs}")
        print(f"📊 Final loaded cogs: {final_cogs}")
        
        self.logger.info("cog_loading_completed",
                        successful_cogs=successful_cogs,
                        failed_cogs=len(failed_cogs),
                        failed_cog_names=failed_cogs,
                        final_loaded_cogs=final_cogs,
                        final_cog_count=len(final_cogs))
        
        # Start health monitoring if enabled
        if settings.HEALTH_CHECKS_ENABLED:
            health_check.start_periodic_checks()
            self.logger.info("health_monitoring_started")

    async def on_ready(self):
        """Called when bot is ready and logged in."""
        startup_duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        # Log cog state when ready
        ready_cogs = list(self.cogs.keys())
        self.logger.info("bot_ready",
                        bot_name=str(self.user),
                        bot_id=self.user.id,
                        guild_count=len(self.guilds),
                        startup_duration_seconds=startup_duration,
                        ready_cogs=ready_cogs,
                        ready_cog_count=len(ready_cogs))
        
        # Send startup alert if enabled
        if settings.ALERTS_ENABLED:
            try:
                await send_startup_alert()
            except Exception as e:
                self.logger.error("startup_alert_failed", error=str(e))
        
        print(f'We have logged in as {self.user}')
        print(f'Bot ID: {self.user.id}')
        print(f'Guilds: {len(self.guilds)}')
        print(f'Startup time: {startup_duration:.2f}s')
        print(f'Loaded cogs: {len(ready_cogs)} - {ready_cogs}')
        print('------')

    async def on_command(self, ctx):
        """Called when a command is invoked."""
        self.logger.info("command_invoked",
                        command_name=ctx.command.name,
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id if ctx.guild else None,
                        channel_id=ctx.channel.id)

    async def on_command_completion(self, ctx):
        """Called when a command completes successfully."""
        # Performance tracking is handled by the performance monitor
        self.logger.debug("command_completed_successfully", 
                         command_name=ctx.command.name)

    async def on_command_error(self, ctx, error):
        """Global error handler for commands."""
        try:
            # Handle with our error system
            handled = await error_handler.handle_command_error(ctx, error)
            
            if not handled:
                # Log unhandled errors
                self.logger.critical("unhandled_command_error",
                                   command=ctx.command.name if ctx.command else "unknown",
                                   error=str(error),
                                   error_type=type(error).__name__)
                
                # Send critical alert
                if settings.ALERTS_ENABLED:
                    await alert_system.send_critical_alert(
                        "Unhandled Command Error",
                        f"Command '{ctx.command.name if ctx.command else 'unknown'}' failed: {str(error)}",
                        command=ctx.command.name if ctx.command else "unknown",
                        user_id=ctx.author.id,
                        guild_id=ctx.guild.id if ctx.guild else None
                    )
        
        except Exception as handler_error:
            # Error in error handler - this is bad
            self.logger.critical("error_handler_failed",
                               original_error=str(error),
                               handler_error=str(handler_error))
            print(f"CRITICAL: Error handler failed: {handler_error}")
        
        # Clean up failed command messages
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    async def on_error(self, event, *args, **kwargs):
        """Global error handler for events."""
        error = sys.exc_info()[1]
        
        try:
            await handle_error(event, error, args=args, kwargs=kwargs)
        except Exception as handler_error:
            self.logger.critical("event_error_handler_failed",
                               event_name=event,
                               original_error=str(error),
                               handler_error=str(handler_error))

    async def close(self):
        """Override close to cleanup resources."""
        self.logger.info("bot_shutdown_initiated")
        
        # Send shutdown alert
        if settings.ALERTS_ENABLED:
            try:
                await send_shutdown_alert()
                # Give a moment for the alert to send
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error("shutdown_alert_failed", error=str(e))
        
        # Stop health monitoring
        if settings.HEALTH_CHECKS_ENABLED:
            health_check.stop_periodic_checks()
            self.logger.info("health_monitoring_stopped")
        
        # Close alert system
        await alert_system.close()
        
        # Call parent close
        await super().close()
        
        self.logger.info("bot_shutdown_completed")


async def main():
    """Main function to start the bot with proper error handling."""
    # Validate settings before starting
    try:
        settings.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    
    # Create and start bot
    bot = RefoldHelperBot()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        asyncio.create_task(bot.close())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.start(settings.BOT_TOKEN)
    except KeyboardInterrupt:
        print("Bot shutdown requested via keyboard interrupt...")
    except Exception as e:
        print(f"Bot crashed: {e}")
        # Try to send critical alert before exiting
        if hasattr(bot, 'logger'):
            bot.logger.critical("bot_crashed", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown complete.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)