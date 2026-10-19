"""
Refold Helper Bot - Main entry point
A comprehensive Discord bot for the Refold language learning community.
"""

import asyncio
import hashlib
import json
import os
import signal
import sys
import traceback
from datetime import datetime

import discord
from discord import app_commands
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
from cogs import COGS, COG_REQUIRED_INTENTS, INTENT_DEGRADED_FEATURES


def build_intents(intent_config):
    """Build the gateway intents from the deployment's privileged-intent flags.

    Only intents this bot actually uses are ever requested. Guild Presences and
    Message Content are never requested - nothing reads presence, Message
    Content was denied and is no longer needed, and asking for an intent the
    app isn't approved for prevents the bot from connecting at all.
    """
    intents = discord.Intents.default()
    intents.members = intent_config.get('members', False)
    return intents


class LoggingCommandTree(app_commands.CommandTree):
    """Command tree that logs each slash-command invocation before it runs."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.type is discord.InteractionType.application_command and interaction.command:
            self.client.logger.info("command_invoked",
                                    command_name=interaction.command.qualified_name,
                                    user_id=interaction.user.id,
                                    guild_id=interaction.guild_id,
                                    channel_id=interaction.channel_id)
        return True


class RefoldHelperBot(commands.Bot):
    """Main bot class with comprehensive logging, monitoring, and error handling."""
    
    def __init__(self):
        # Setup logging first
        setup_logging(**settings.get_log_config())
        self.logger = get_logger('bot.main')
        
        # Initialize Discord bot. Privileged intents are opt-in per deployment
        # so a revoked or pending intent degrades the bot instead of grounding it.
        self.intent_config = settings.get_intent_config()
        intents = build_intents(self.intent_config)

        # Every command is a slash command. Message Content is not granted, so
        # a text prefix can never match; mention-only means no handler ever
        # tries to parse ordinary members' messages.
        # Commands are server-only: Discord ignores default_permissions in DMs,
        # so admin commands would otherwise be offered to anyone there.
        super().__init__(
            intents=intents,
            command_prefix=commands.when_mentioned,
            help_command=None,
            tree_cls=LoggingCommandTree,
            allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=False,
                                                            private_channel=False),
        )
        self.tree.on_error = self.on_app_command_error

        self._log_intent_status()

        # Cogs we will actually attempt, so health checks don't report a
        # deliberately skipped cog as a failure.
        self.expected_cogs = [c for c in COGS if self._skip_reason(c) is None]
        self.skipped_cogs = {c: self._skip_reason(c) for c in COGS
                             if self._skip_reason(c) is not None}

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

    def _log_intent_status(self):
        """Announce which privileged intents are on, and what is lost without them."""
        granted = sorted(k for k, v in self.intent_config.items() if v)
        missing = sorted(k for k, v in self.intent_config.items() if not v)

        self.logger.info("privileged_intents_configured",
                         granted=granted, missing=missing)
        print(f"Privileged intents enabled: {granted or 'none'}")

        for intent in missing:
            features = INTENT_DEGRADED_FEATURES.get(intent, [])
            self.logger.warning("privileged_intent_missing",
                                intent=intent, degraded_features=features)
            print(f"\n[DEGRADED] '{intent}' intent is OFF - unavailable:")
            for feature in features:
                print(f"  - {feature}")
        if missing:
            print("\nEnable with INTENT_GUILD_MEMBERS=true once Discord approves the request.\n")

    def _skip_reason(self, cog):
        """Return the missing intent blocking this cog, or None if safe to load."""
        for intent in COG_REQUIRED_INTENTS.get(cog, ()):
            if not self.intent_config.get(intent, False):
                return intent
        return None

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
                expected_cogs = len(self.expected_cogs)
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
        self.logger.info("bot_setup_starting",
                         cog_count=len(self.expected_cogs),
                         skipped_cogs=self.skipped_cogs)

        for cog, intent in self.skipped_cogs.items():
            print(f"\n=== SKIPPING COG: {cog} (requires '{intent}' intent) ===")
            self.logger.warning("cog_skipped_missing_intent",
                                cog_name=cog, required_intent=intent)

        # Load cogs with performance tracking
        successful_cogs = 0
        failed_cogs = []

        for i, cog in enumerate(self.expected_cogs):
            print(f"\n=== LOADING COG {i+1}/{len(self.expected_cogs)}: {cog} ===")
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
        
        await self.sync_commands_if_changed()

        # Start health monitoring if enabled
        if settings.HEALTH_CHECKS_ENABLED:
            health_check.start_periodic_checks()
            self.logger.info("health_monitoring_started")

    def _command_tree_hash(self) -> str:
        """Fingerprint of the global slash-command definitions."""
        payload = [cmd.to_dict(self.tree) for cmd in self.tree.get_commands()]
        blob = json.dumps(sorted(payload, key=lambda c: c['name']), sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()

    async def sync_commands_if_changed(self, *, force: bool = False) -> bool:
        """Push slash commands to Discord, but only when their definitions changed.

        Syncing on every restart burns a tightly rate-limited endpoint, so the
        last synced fingerprint is kept in the data dir and compared first.
        """
        hash_file = os.path.join(settings.DATA_DIR, 'command_tree.sha256')
        current = self._command_tree_hash()
        try:
            with open(hash_file) as f:
                previous = f.read().strip()
        except OSError:
            previous = None

        if not force and current == previous:
            self.logger.info("command_sync_skipped", reason="unchanged")
            return False

        try:
            synced = await self.tree.sync()
        except discord.HTTPException as e:
            self.logger.error("command_sync_failed", error=str(e))
            print(f"❌ Slash command sync failed: {e}")
            return False

        try:
            os.makedirs(settings.DATA_DIR, exist_ok=True)
            with open(hash_file, 'w') as f:
                f.write(current)
        except OSError as e:
            self.logger.warning("command_sync_hash_write_failed", error=str(e))

        self.logger.info("commands_synced", count=len(synced))
        print(f"🔄 Synced {len(synced)} slash commands")
        return True

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

    async def on_app_command_completion(self, interaction, command):
        """Called when a slash command completes successfully."""
        # Performance tracking is handled by the performance monitor
        self.logger.debug("command_completed_successfully",
                         command_name=command.qualified_name)

    async def on_app_command_error(self, interaction: discord.Interaction, error):
        """Global error handler for slash commands."""
        command_name = interaction.command.qualified_name if interaction.command else "unknown"
        try:
            # Handle with our error system
            handled = await error_handler.handle_command_error(interaction, error)

            if not handled:
                # Log unhandled errors
                self.logger.critical("unhandled_command_error",
                                   command=command_name,
                                   error=str(error),
                                   error_type=type(error).__name__)

                # Send critical alert
                if settings.ALERTS_ENABLED:
                    await alert_system.send_critical_alert(
                        "Unhandled Command Error",
                        f"Command '{command_name}' failed: {str(error)}",
                        command=command_name,
                        user_id=interaction.user.id,
                        guild_id=interaction.guild_id
                    )

        except Exception as handler_error:
            # Error in error handler - this is bad
            self.logger.critical("error_handler_failed",
                               original_error=str(error),
                               handler_error=str(handler_error))
            print(f"CRITICAL: Error handler failed: {handler_error}")

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
    except discord.PrivilegedIntentsRequired:
        # We asked for an intent Discord has not granted, so the gateway
        # refused the handshake (close code 4014) and nothing started.
        enabled = sorted(k for k, v in bot.intent_config.items() if v)
        print("\n" + "=" * 72)
        print("STARTUP FAILED: Discord refused a privileged intent request.")
        print(f"Currently requesting: {enabled or 'none'}")
        print("")
        print("An intent is enabled here that the app is not approved for.")
        print("Set the matching env var to false to get the bot back online:")
        print("  INTENT_GUILD_MEMBERS=false")
        print("")
        print("Then check the approval state under Bot > Privileged Gateway")
        print("Intents in the Discord Developer Portal.")
        print("=" * 72 + "\n")
        bot.logger.critical("privileged_intents_required",
                            requested=enabled,
                            note="Gateway refused handshake; disable unapproved intents")
        sys.exit(1)
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