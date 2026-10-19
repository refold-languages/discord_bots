"""
Community cog for Refold Helper Bot.
Handles projects, automated threads, accountability features, and community management with comprehensive logging and monitoring.
"""

import time
from datetime import datetime

from typing import List, Optional

import discord
import pytz
from discord import app_commands
from discord.ext import commands

from services import ProjectService, ThreadService
from config.settings import settings
from utils import (
    get_logger, performance_monitor, handle_error,
    DiscordError, ValidationError, safe_execute
)
from utils.interactions import respond, confirm

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

    thread_channels = app_commands.Group(
        name='threadchannels', description='Channels where every post gets its own thread',
        default_permissions=discord.Permissions(manage_channels=True), guild_only=True)
    poll_channels = app_commands.Group(
        name='pollchannels', description='Channels where every post gets up/down vote reactions',
        default_permissions=discord.Permissions(manage_channels=True), guild_only=True)

    # Thread channel management
    @thread_channels.command(name='add', description='Auto-create a thread for every post in a channel')
    @app_commands.describe(channel='Channel to add (default: this one)')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_thread_channel(self, interaction: discord.Interaction,
                                 channel: Optional[discord.TextChannel] = None):
        """Add a channel (default: the current one) to the auto-thread list."""
        channel_id = channel.id if channel else interaction.channel_id
        try:
            success = await self.thread_service.add_thread_channel(channel_id)
        except Exception as e:
            raise DiscordError("Failed to add thread channel", discord_error=e)
        if success:
            await interaction.response.send_message(f'✅ <#{channel_id}> added to auto-thread list.')
        else:
            await interaction.response.send_message(f'⚠️ <#{channel_id}> is already in the auto-thread list.',
                                                    ephemeral=True)

    @thread_channels.command(name='remove', description='Stop auto-creating threads in a channel')
    @app_commands.describe(channel='Channel to remove (default: this one)')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_thread_channel(self, interaction: discord.Interaction,
                                    channel: Optional[discord.TextChannel] = None):
        """Remove a channel (default: the current one) from the auto-thread list."""
        channel_id = channel.id if channel else interaction.channel_id
        try:
            success = await self.thread_service.remove_thread_channel(channel_id)
        except Exception as e:
            raise DiscordError("Failed to remove thread channel", discord_error=e)
        if success:
            await interaction.response.send_message(f'✅ <#{channel_id}> removed from auto-thread list.')
        else:
            await interaction.response.send_message(f'⚠️ <#{channel_id}> is not in the auto-thread list.',
                                                    ephemeral=True)

    @thread_channels.command(name='clear', description='Remove every channel from the auto-thread list')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def clear_thread_channels(self, interaction: discord.Interaction):
        """Clear all auto-thread channels."""
        if not await confirm(interaction, "⚠️ Remove **every** channel from the auto-thread list?",
                             confirm_label='Clear all'):
            return
        try:
            success = await self.thread_service.clear_all_thread_channels()
        except Exception as e:
            raise DiscordError("Failed to clear thread channels", discord_error=e)
        if success:
            await respond(interaction, '✅ All auto-thread channels cleared.')
        else:
            await respond(interaction, '❌ Failed to clear auto-thread channels.', ephemeral=True)

    @thread_channels.command(name='list', description='List the auto-thread channels')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def list_thread_channels(self, interaction: discord.Interaction):
        """List all auto-thread channels."""
        try:
            channels = self.thread_service.get_thread_channels()
        except Exception as e:
            raise DiscordError("Failed to list thread channels", discord_error=e)
        if not channels:
            await interaction.response.send_message("📋 No auto-thread channels configured.", ephemeral=True)
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
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Poll channel management
    @poll_channels.command(name='add', description='Add vote reactions to every post in a channel')
    @app_commands.describe(channel='Channel to add (default: this one)')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_poll_channel(self, interaction: discord.Interaction,
                               channel: Optional[discord.TextChannel] = None):
        """Add a channel (default: the current one) to the auto-poll list."""
        channel_id = channel.id if channel else interaction.channel_id
        try:
            success = await self.thread_service.add_poll_channel(channel_id)
        except Exception as e:
            raise DiscordError("Failed to set poll channel", discord_error=e)
        if success:
            await interaction.response.send_message(f'✅ <#{channel_id}> added to auto-poll list.')
        else:
            await interaction.response.send_message(f'⚠️ <#{channel_id}> is already in the auto-poll list.',
                                                    ephemeral=True)

    @poll_channels.command(name='remove', description='Stop adding vote reactions in a channel')
    @app_commands.describe(channel='Channel to remove (default: this one)')
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_poll_channel(self, interaction: discord.Interaction,
                                  channel: Optional[discord.TextChannel] = None):
        """Remove a channel (default: the current one) from the auto-poll list."""
        channel_id = channel.id if channel else interaction.channel_id
        try:
            success = await self.thread_service.remove_poll_channel(channel_id)
        except Exception as e:
            raise DiscordError("Failed to remove poll channel", discord_error=e)
        if success:
            await interaction.response.send_message(f'✅ <#{channel_id}> removed from auto-poll list.')
        else:
            await interaction.response.send_message(f'⚠️ <#{channel_id}> is not in the auto-poll list.',
                                                    ephemeral=True)

    # Auto-threading and poll reactions
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle auto-threading and poll reactions with comprehensive error handling."""
        if message.author == self.bot.user:
            return
        
        try:
            if self.thread_service.should_create_thread(message.channel.id):
                async with performance_monitor.track("auto_create_thread", 
                                                    channel_id=message.channel.id):
                    # Content is empty without the Message Content intent, so
                    # fall back to a name built from metadata we always get.
                    thread_name = self.thread_service.generate_thread_name_from_message(
                        message.content,
                        fallback=f"{message.author.display_name} – {message.created_at:%b %d}")
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
    @app_commands.command(description='List all active community projects')
    async def listprojects(self, interaction: discord.Interaction):
        """List all active projects."""
        try:
            projects = self.project_service.get_all_projects()
        except Exception as e:
            raise DiscordError("Failed to list projects", discord_error=e)

        if not projects:
            await interaction.response.send_message("📋 No active projects found.")
            return

        embed = discord.Embed(title='Current Community Projects', description='', color=0x8566FF)

        for name, project in projects.items():
            embed.add_field(
                name=f"🎯 {name.title()}",
                value=f'**Leader:** {project.leader}\n**Description:** {project.description}',
                inline=False
            )

        embed.set_footer(text=f"Total projects: {len(projects)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description='Create a new community project with a private channel')
    @app_commands.describe(name='Project name (becomes the channel name)', leader='Who leads it',
                           description='What the project is about')
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def createproject(self, interaction: discord.Interaction, name: str, leader: str,
                            description: str):
        """Create a new community project with private channel."""
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
        await interaction.response.send_message("🏗️ Setting up project channel...")
        
        guild = interaction.guild
        clean_name = name.lower().strip()
        try:
            category_name = "COMMUNITY PROJECTS"
            category = discord.utils.get(guild.categories, name=category_name)
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True)
            }

            if category is None:
                category = await guild.create_category(category_name, reason="Community project category")
            
            channel = await guild.create_text_channel(
                name=clean_name, 
                overwrites=overwrites, 
                reason=f"Project channel for {clean_name}",
                category=category
            )
            
            invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
            await interaction.user.send(f'🎯 Project "{clean_name}" created successfully!\n📨 Channel invite: {invitelink}')
            await respond(interaction, f'✅ Project "{clean_name}" created! Check your DMs for the channel invite.')
            
        except discord.HTTPException as e:
            # If Discord channel creation fails, clean up the project
            await self.project_service.delete_project(clean_name)
            raise DiscordError(f"Failed to create Discord channel: {str(e)}", discord_error=e)

    @app_commands.command(description='Join an existing community project')
    @app_commands.describe(name='Project to join')
    @app_commands.guild_only()
    async def joinproject(self, interaction: discord.Interaction, name: str):
        """Join an existing community project."""
        project = self.project_service.get_project(name)
        if not project:
            available_projects = list(self.project_service.get_all_projects().keys())
            if available_projects:
                projects_list = ", ".join(available_projects[:5])
                if len(available_projects) > 5:
                    projects_list += f" (and {len(available_projects) - 5} more)"
                await interaction.response.send_message(
                    f"❌ Project not found. Available projects: {projects_list}", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "❌ No active projects found. Use `/listprojects` to see available projects.",
                    ephemeral=True)
            return
        
        # Find Discord channel and grant access
        channel = discord.utils.get(interaction.guild.channels, name=project.name)
        if not channel:
            raise DiscordError(
                f"Project channel for '{project.name}' not found",
                user_message="Project channel not found. Please contact an administrator."
            )
        
        try:
            overwrite = discord.PermissionOverwrite()
            overwrite.read_messages = True
            await channel.set_permissions(interaction.user, overwrite=overwrite)
            
            invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
            await interaction.user.send(f'🎯 Welcome to "{project.name}"!\n📨 Direct link: {invitelink}')
            await interaction.response.send_message(
                f'✅ You\'ve been added to "{project.name}"! Check your DMs for the channel link.',
                ephemeral=True)
            
        except discord.HTTPException as e:
            raise DiscordError(f"Failed to grant project access: {str(e)}", discord_error=e)

    @joinproject.autocomplete('name')
    async def _project_autocomplete(self, interaction: discord.Interaction,
                                    current: str) -> List[app_commands.Choice[str]]:
        current = current.lower()
        names = [n for n in self.project_service.get_all_projects().keys() if current in n.lower()]
        return [app_commands.Choice(name=n[:100], value=n[:100]) for n in names[:25]]


async def setup(bot):
    """Add the Community cog to the bot."""
    await bot.add_cog(Community(bot))