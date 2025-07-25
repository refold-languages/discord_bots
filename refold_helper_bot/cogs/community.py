"""
Community cog for Refold Helper Bot.
Handles projects, automated threads, accountability features, and community management with comprehensive logging and monitoring.
"""

import asyncio
import time
from datetime import datetime

import discord
import pytz
from discord.ext import commands, tasks

from services import ProjectService, ThreadService
from config.settings import settings
from utils import (
    get_logger, performance_monitor, handle_error,
    DiscordError, ValidationError, safe_execute
)


def track_command_performance(func):
    """Decorator to track command performance and add comprehensive logging."""
    async def wrapper(self, ctx, *args, **kwargs):
        start_time = time.perf_counter()
        command_name = ctx.command.name if ctx.command else func.__name__
        
        # Log command start
        self.logger.command_start(
            command_name,
            ctx.author.id,
            ctx.guild.id if ctx.guild else None,
            channel_id=ctx.channel.id
        )
        
        try:
            async with performance_monitor.track(f"command_{command_name}", 
                                                user_id=ctx.author.id,
                                                guild_id=ctx.guild.id if ctx.guild else None):
                result = await func(self, ctx, *args, **kwargs)
                
                # Log successful completion
                duration_ms = (time.perf_counter() - start_time) * 1000
                self.logger.command_success(command_name, duration_ms)
                
                # Check for slow commands
                if duration_ms > settings.SLOW_COMMAND_THRESHOLD_MS:
                    self.logger.warning("slow_command_detected",
                                      command_name=command_name,
                                      duration_ms=duration_ms,
                                      threshold_ms=settings.SLOW_COMMAND_THRESHOLD_MS,
                                      user_id=ctx.author.id)
                
                return result
                
        except Exception as e:
            # Log command error
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.command_error(command_name, str(e), duration_ms)
            
            # Let error handler deal with it
            await handle_error(ctx, e)
            
    return wrapper


class Community(commands.Cog):
    """Community management features with comprehensive monitoring and error handling."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.community')
        self.project_service = ProjectService()
        self.thread_service = ThreadService()

    async def cog_load(self):
        """Initialize services and start automated tasks when cog loads (non-blocking)."""
        self.logger.info("community_cog_loading")
        
        try:
            # Initialize services
            self.project_service.initialize()
            self.thread_service.initialize()
            
            # Schedule tasks to start, but don't block cog loading
            asyncio.create_task(self._schedule_daily_thread())
            asyncio.create_task(self._schedule_grads_thread())
            
            self.logger.info("community_cog_loaded_successfully")
            
        except Exception as e:
            self.logger.error("community_cog_load_failed",
                            error=str(e),
                            error_type=type(e).__name__)
            raise

    def cog_unload(self):
        """Clean up tasks when cog unloads."""
        self.logger.info("community_cog_unloading")
        
        if hasattr(self, 'create_daily_thread') and self.create_daily_thread.is_running():
            self.create_daily_thread.cancel()
            self.logger.info("daily_thread_task_cancelled")
            
        if hasattr(self, 'grads_create_daily_thread') and self.grads_create_daily_thread.is_running():
            self.grads_create_daily_thread.cancel()
            self.logger.info("grads_thread_task_cancelled")
        
        self.logger.info("community_cog_unloaded")

    # Automated thread scheduling
    async def _schedule_daily_thread(self):
        """Schedule daily thread task (non-blocking)."""
        await self.bot.wait_until_ready()
        
        try:
            now = datetime.now(pytz.timezone(settings.TIMEZONE))
            first_run_time = self.thread_service.calculate_next_daily_occurrence()
            initial_delay = (first_run_time - now).total_seconds()
            
            self.logger.info("daily_thread_scheduled",
                           next_run_time=first_run_time.isoformat(),
                           initial_delay_seconds=initial_delay)
            
            await asyncio.sleep(initial_delay)
            self.create_daily_thread.start()
            
        except Exception as e:
            self.logger.error("daily_thread_scheduling_failed",
                            error=str(e),
                            error_type=type(e).__name__)

    async def _schedule_grads_thread(self):
        """Schedule weekly graduate thread task (non-blocking)."""
        await self.bot.wait_until_ready()
        
        try:
            now = datetime.now(pytz.timezone(settings.TIMEZONE))
            first_run_time = self.thread_service.calculate_next_weekly_occurrence()
            initial_delay = (first_run_time - now).total_seconds()
            
            self.logger.info("grads_thread_scheduled",
                           next_run_time=first_run_time.isoformat(),
                           initial_delay_seconds=initial_delay)
            
            await asyncio.sleep(initial_delay)
            self.grads_create_daily_thread.start()
            
        except Exception as e:
            self.logger.error("grads_thread_scheduling_failed",
                            error=str(e),
                            error_type=type(e).__name__)

    @tasks.loop(hours=24)
    async def create_daily_thread(self):
        """Create daily accountability threads."""
        try:
            async with performance_monitor.track("create_daily_accountability_thread"):
                now = datetime.now().astimezone(pytz.timezone(settings.TIMEZONE))
                timestamp = int(now.timestamp())
                
                # Generate message using service
                message_data = self.thread_service.generate_daily_accountability_message(timestamp)
                
                # Send to all accountability channels
                channels_processed = 0
                channels_failed = 0
                
                for channel_id in self.thread_service.get_accountability_channels():
                    try:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            message = await channel.send(message_data.content)
                            await channel.create_thread(name=message_data.thread_name, message=message)
                            channels_processed += 1
                            
                            self.logger.info("daily_thread_created",
                                           channel_id=channel_id,
                                           thread_name=message_data.thread_name)
                        else:
                            self.logger.warning("daily_thread_channel_not_found",
                                              channel_id=channel_id)
                            channels_failed += 1
                            
                    except discord.DiscordException as e:
                        self.logger.error("daily_thread_creation_failed",
                                        channel_id=channel_id,
                                        error=str(e),
                                        error_type=type(e).__name__)
                        channels_failed += 1
                
                self.logger.info("daily_thread_creation_completed",
                               channels_processed=channels_processed,
                               channels_failed=channels_failed,
                               timestamp=timestamp)
                
        except Exception as e:
            self.logger.error("daily_thread_task_failed",
                            error=str(e),
                            error_type=type(e).__name__)

    @tasks.loop(hours=168)  # Weekly
    async def grads_create_daily_thread(self):
        """Create weekly graduate check-in threads."""
        try:
            async with performance_monitor.track("create_weekly_graduate_thread"):
                now = datetime.now().astimezone(pytz.timezone(settings.TIMEZONE))
                timestamp = int(now.timestamp())
                
                # Generate message using service
                message_data = self.thread_service.generate_weekly_graduate_message(timestamp)
                
                # Send to all graduate channels
                channels_processed = 0
                channels_failed = 0
                
                for channel_id in self.thread_service.get_graduate_channels():
                    try:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            message = await channel.send(message_data.content)
                            await channel.create_thread(name=message_data.thread_name, message=message)
                            channels_processed += 1
                            
                            self.logger.info("graduate_thread_created",
                                           channel_id=channel_id,
                                           thread_name=message_data.thread_name)
                        else:
                            self.logger.warning("graduate_thread_channel_not_found",
                                              channel_id=channel_id)
                            channels_failed += 1
                            
                    except discord.DiscordException as e:
                        self.logger.error("graduate_thread_creation_failed",
                                        channel_id=channel_id,
                                        error=str(e),
                                        error_type=type(e).__name__)
                        channels_failed += 1
                
                self.logger.info("graduate_thread_creation_completed",
                               channels_processed=channels_processed,
                               channels_failed=channels_failed,
                               timestamp=timestamp)
                
        except Exception as e:
            self.logger.error("graduate_thread_task_failed",
                            error=str(e),
                            error_type=type(e).__name__)

    # Thread channel management
    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    @track_command_performance
    async def setthreadchannel(self, ctx):
        """Set current channel as auto-thread channel."""
        try:
            success = await self.thread_service.add_thread_channel(ctx.channel.id)
            if success:
                await ctx.send('✅ Channel added to auto-thread list.')
            else:
                await ctx.send('⚠️ This channel is already in the auto-thread list.')
                
        except Exception as e:
            raise DiscordError("Failed to set thread channel", discord_error=e)

    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    @track_command_performance
    async def addthreadchannel(self, ctx, channel_id: str):
        """Add specified channel as auto-thread channel."""
        try:
            channel_id_int = int(channel_id)
        except ValueError:
            raise ValidationError("Invalid channel ID format", field="channel_id", value=channel_id)
        
        try:
            success = await self.thread_service.add_thread_channel(channel_id_int)
            if success:
                await ctx.send(f'✅ Channel {channel_id_int} added to auto-thread list.')
            else:
                await ctx.send(f'⚠️ Channel {channel_id_int} is already in the auto-thread list.')
                
        except Exception as e:
            raise DiscordError("Failed to add thread channel", discord_error=e)

    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    @track_command_performance
    async def removethreadchannel(self, ctx):
        """Remove current channel from auto-thread list."""
        try:
            success = await self.thread_service.remove_thread_channel(ctx.channel.id)
            if success:
                await ctx.send('✅ Channel removed from auto-thread list.')
            else:
                await ctx.send('⚠️ This channel is not in the auto-thread list.')
                
        except Exception as e:
            raise DiscordError("Failed to remove thread channel", discord_error=e)

    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    @track_command_performance
    async def clearthreadchannels(self, ctx):
        """Clear all auto-thread channels."""
        try:
            success = await self.thread_service.clear_all_thread_channels()
            if success:
                await ctx.send('✅ All auto-thread channels cleared.')
            else:
                await ctx.send('❌ Failed to clear auto-thread channels.')
                
        except Exception as e:
            raise DiscordError("Failed to clear thread channels", discord_error=e)

    # Poll channel management
    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    @track_command_performance
    async def setpollchannel(self, ctx):
        """Set current channel as auto-poll channel."""
        try:
            success = await self.thread_service.add_poll_channel(ctx.channel.id)
            if success:
                await ctx.send('✅ Channel added to auto-poll list.')
            else:
                await ctx.send('⚠️ This channel is already in the auto-poll list.')
                
        except Exception as e:
            raise DiscordError("Failed to set poll channel", discord_error=e)

    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    @track_command_performance
    async def removepollchannel(self, ctx):
        """Remove current channel from auto-poll list."""
        try:
            success = await self.thread_service.remove_poll_channel(ctx.channel.id)
            if success:
                await ctx.send('✅ Channel removed from auto-poll list.')
            else:
                await ctx.send('⚠️ This channel is not in the auto-poll list.')
                
        except Exception as e:
            raise DiscordError("Failed to remove poll channel", discord_error=e)

    # Auto-threading and poll reactions
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle auto-threading and poll reactions with comprehensive error handling."""
        if message.author == self.bot.user or message.content.startswith(self.bot.command_prefix):
            return
        
        try:
            if self.thread_service.should_create_thread(message.channel.id):
                async with performance_monitor.track("auto_create_thread", 
                                                    channel_id=message.channel.id):
                    thread_name = self.thread_service.generate_thread_name_from_message(message.content)
                    await message.create_thread(name=thread_name)
                    
                    self.logger.info("auto_thread_created",
                                   channel_id=message.channel.id,
                                   thread_name=thread_name,
                                   message_length=len(message.content))
                    
            elif self.thread_service.should_add_poll_reactions(message.channel.id):
                async with performance_monitor.track("auto_add_poll_reactions",
                                                    channel_id=message.channel.id):
                    upvote, downvote = self.thread_service.get_poll_reactions()
                    await message.add_reaction(upvote)
                    await message.add_reaction(downvote)
                    
                    self.logger.info("auto_poll_reactions_added",
                                   channel_id=message.channel.id,
                                   message_id=message.id)
                    
        except discord.DiscordException as e:
            self.logger.error("auto_message_processing_failed",
                            channel_id=message.channel.id,
                            message_id=message.id,
                            error=str(e),
                            error_type=type(e).__name__)
        except Exception as e:
            self.logger.error("unexpected_auto_message_error",
                            channel_id=message.channel.id,
                            message_id=message.id,
                            error=str(e),
                            error_type=type(e).__name__)

    # Project management system
    @commands.command(hidden=True)
    @track_command_performance
    async def listprojects(self, ctx):
        """List all active projects."""
        try:
            projects = self.project_service.get_all_projects()
            
            if not projects:
                await ctx.send("📋 No active projects found.")
                return
            
            embed = discord.Embed(title='Current Community Projects', description='', color=0x8566FF)
            
            for name, project in projects.items():
                embed.add_field(
                    name=f"🎯 {name.title()}", 
                    value=f'**Leader:** {project.leader}\n**Description:** {project.description}', 
                    inline=False
                )
            
            embed.set_footer(text=f"Total projects: {len(projects)}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            raise DiscordError("Failed to list projects", discord_error=e)

    @commands.command(hidden=True)
    @commands.has_permissions(manage_channels=True)
    @track_command_performance
    async def createproject(self, ctx, name: str = None, leader: str = None, *, description: str = None):
        """Create a new community project with private channel."""
        if not name or not leader or not description:
            raise ValidationError(
                "Missing required project information",
                user_message="Please provide all required fields: `!createproject [name] [leader] [description]`"
            )
        
        # Validate project name first
        is_valid, error_msg = self.project_service.validate_project_name(name)
        if not is_valid:
            raise ValidationError(f"Invalid project name: {error_msg}", field="name", value=name)
        
        # Create project in service
        success, message = await self.project_service.create_project(name, leader, description)
        if not success:
            if "already exists" in message:
                raise ValidationError(message, field="name", value=name)
            else:
                raise DiscordError(f"Failed to create project: {message}")
        
        # If project created successfully, set up Discord channel
        await ctx.send("🏗️ Setting up project channel...")
        
        try:
            clean_name = name.lower().strip()
            category_name = "COMMUNITY PROJECTS"
            category = discord.utils.get(ctx.guild.categories, name=category_name)
            
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False), 
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True), 
                ctx.author: discord.PermissionOverwrite(read_messages=True)
            }

            if category is None:
                category = await ctx.guild.create_category(category_name, reason="Community project category")
            
            channel = await ctx.guild.create_text_channel(
                name=clean_name, 
                overwrites=overwrites, 
                reason=f"Project channel for {clean_name}",
                category=category
            )
            
            invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
            await ctx.author.send(f'🎯 Project "{clean_name}" created successfully!\n📨 Channel invite: {invitelink}')
            await ctx.send(f'✅ Project "{clean_name}" created! Check your DMs for the channel invite.')
            
        except discord.HTTPException as e:
            # If Discord channel creation fails, clean up the project
            await self.project_service.delete_project(clean_name)
            raise DiscordError(f"Failed to create Discord channel: {str(e)}", discord_error=e)

    @commands.command()
    @track_command_performance
    async def joinproject(self, ctx, *, name: str = None):
        """Join an existing community project."""
        if not name:
            raise ValidationError(
                "Project name is required",
                user_message="Which project would you like to join? Use: `!joinproject [projectname]`"
            )
        
        project = self.project_service.get_project(name)
        if not project:
            available_projects = list(self.project_service.get_all_projects().keys())
            if available_projects:
                projects_list = ", ".join(available_projects[:5])
                if len(available_projects) > 5:
                    projects_list += f" (and {len(available_projects) - 5} more)"
                raise ValidationError(
                    f"Project '{name}' not found",
                    user_message=f"Project not found. Available projects: {projects_list}"
                )
            else:
                raise ValidationError(
                    "No projects exist",
                    user_message="No active projects found. Use `!listprojects` to see available projects."
                )
        
        # Find Discord channel and grant access
        channel = discord.utils.get(ctx.guild.channels, name=project.name)
        if not channel:
            raise DiscordError(
                f"Project channel for '{project.name}' not found",
                user_message="Project channel not found. Please contact an administrator."
            )
        
        try:
            overwrite = discord.PermissionOverwrite()
            overwrite.read_messages = True
            await channel.set_permissions(ctx.author, overwrite=overwrite)
            
            invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
            await ctx.author.send(f'🎯 Welcome to "{project.name}"!\n📨 Direct link: {invitelink}')
            await ctx.send(f'✅ You\'ve been added to "{project.name}"! Check your DMs for the channel link.')
            
        except discord.HTTPException as e:
            raise DiscordError(f"Failed to grant project access: {str(e)}", discord_error=e)


async def setup(bot):
    """Add the Community cog to the bot."""
    await bot.add_cog(Community(bot))