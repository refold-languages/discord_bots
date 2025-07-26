"""
Community cog for Refold Helper Bot.
Handles projects, automated threads, accountability features, and community management with comprehensive logging and monitoring.
"""

import time
from datetime import datetime

import discord
import pytz
from discord.ext import commands

from services import ProjectService, ThreadService
from config.settings import settings
from utils import (
    get_logger, performance_monitor, handle_error,
    DiscordError, ValidationError, safe_execute
)

class Community(commands.Cog):
    """Community management features with comprehensive monitoring and error handling."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.community')
        self.project_service = ProjectService()
        self.thread_service = ThreadService()

    async def cog_load(self):
        """Initialize services when cog loads."""
        self.logger.info("community_cog_loading")
        
        try:
            # Initialize services
            self.project_service.initialize()
            self.thread_service.initialize()
            
            self.logger.info("community_cog_loaded_successfully")
            
        except Exception as e:
            self.logger.error("community_cog_load_failed",
                            error=str(e),
                            error_type=type(e).__name__)
            raise

    def cog_unload(self):
        """Clean up when cog unloads."""
        self.logger.info("community_cog_unloading")
        self.logger.info("community_cog_unloaded")

    # Thread channel management
    @commands.command()
    @commands.has_permissions(manage_channels=True)
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

    @commands.command()
    @commands.has_permissions(manage_channels=True)
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

    @commands.command()
    @commands.has_permissions(manage_channels=True)
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

    @commands.command()
    @commands.has_permissions(manage_channels=True)
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

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def listthreadchannels(self, ctx):
        """List all auto-thread channels."""
        try:
            channels = self.thread_service.get_thread_channels()
            if not channels:
                await ctx.send("📋 No auto-thread channels configured.")
                return
            
            channel_list = []
            for channel_id in channels:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    channel_list.append(f"• {channel.name} ({channel_id})")
                else:
                    channel_list.append(f"• Unknown Channel ({channel_id})")
            
            embed = discord.Embed(title='Auto-Thread Channels', color=0x8566FF)
            embed.description = '\n'.join(channel_list)
            await ctx.send(embed=embed)
            
        except Exception as e:
            raise DiscordError("Failed to list thread channels", discord_error=e)

    @commands.command()
    async def debugcommunity(self, ctx):
        """Debug command to test if community cog is loaded."""
        await ctx.send("✅ Community cog is loaded and working!")
        
        # Test the data manager
        try:
            channels = self.thread_service.get_thread_channels()
            await ctx.send(f"📊 Thread channels: {len(channels)} configured")
        except Exception as e:
            await ctx.send(f"❌ Thread service error: {e}")
        
        # Test services
        try:
            summary = self.thread_service.get_channel_configuration_summary()
            await ctx.send(f"📋 Channel config: {summary}")
        except Exception as e:
            await ctx.send(f"❌ Config summary error: {e}")

    # Poll channel management
    @commands.command()
    @commands.has_permissions(manage_channels=True)
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

    @commands.command()
    @commands.has_permissions(manage_channels=True)
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
    @commands.command()
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

    @commands.command()
    @commands.has_permissions(manage_channels=True)
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