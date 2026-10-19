"""
Roles cog for Refold Helper Bot.
Handles cross-server role sync, reaction roles, and special role features.
"""

import discord
from discord import app_commands
from discord.ext import commands

import time
from typing import Dict, Optional

from services import RoleService

# Each sync makes one member lookup per language server, so rate-limit presses.
ROLE_SYNC_COOLDOWN_SECONDS = 60


class SyncRolesView(discord.ui.View):
    """Persistent "Sync my roles" button for language-server welcome channels.

    Without the Guild Members intent the bot never hears about joins, so
    members trigger the cross-server sync themselves. Survives restarts
    (timeout=None + fixed custom_id, re-registered in cog_load).
    """

    def __init__(self, cog: 'Roles'):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label='Sync my roles', style=discord.ButtonStyle.primary,
                       custom_id='refold:roles:sync')
    async def sync_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.sync_member_roles(interaction)


class Roles(commands.Cog):
    """Role management system for cross-server sync and reaction roles."""
    
    def __init__(self, bot):
        self.bot = bot
        self.role_service = RoleService()
        self._last_role_sync: Dict[int, float] = {}
    
    async def cog_load(self):
        """Initialize the role service when cog loads."""
        self.role_service.initialize()
        self.bot.add_view(SyncRolesView(self))

    async def _resolve_member(self, guild, user_id, payload_member=None):
        """Resolve a member without depending on the gateway member cache.

        Reaction roles must keep working when the Guild Members intent is
        unavailable, which leaves that cache empty. Three sources, cheapest
        first:

        1. ``payload.member`` - Discord includes it on reaction *adds* in a
           guild regardless of intents. Removals never carry it.
        2. The member cache - populated only with the members intent.
        3. An HTTP fetch - always works, but costs a request, so it is last.
        """
        if payload_member is not None:
            return payload_member

        member = guild.get_member(user_id)
        if member is not None:
            return member

        try:
            return await guild.fetch_member(user_id)
        except discord.HTTPException:
            return None

    async def _assign_role_to_member(self, member, role_id):
        """Assign a role to a member in the main server (Discord API operation)."""
        from config.settings import settings
        
        main_guild = await self.bot.fetch_guild(settings.MAIN_SERVER_ID)
        if main_guild:
            roles = await main_guild.fetch_roles()
            role = discord.utils.find(lambda r: r.id == int(role_id), roles)
            if role:
                try:
                    member_in_main_guild = await main_guild.fetch_member(member.id)
                    await member_in_main_guild.add_roles(role)
                except discord.HTTPException:
                    pass

    async def _remove_role_from_member(self, member, role_id):
        """Remove a role from a member in the main server (Discord API operation)."""
        from config.settings import settings
        
        main_guild = await self.bot.fetch_guild(settings.MAIN_SERVER_ID)
        if main_guild:
            roles = await main_guild.fetch_roles()
            role = discord.utils.find(lambda r: r.id == int(role_id), roles)
            if role:
                try:
                    member_in_main_guild = await main_guild.fetch_member(member.id)
                    await member_in_main_guild.remove_roles(role)
                except discord.HTTPException:
                    pass

    # Cross-server role sync events
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member joining - assign language role in main server."""
        if self.role_service.should_sync_role(member.guild.id):
            role_id = self.role_service.get_role_for_guild(member.guild.id)
            if role_id:
                await self._assign_role_to_member(member, role_id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leaving - remove language role from main server."""
        if self.role_service.should_sync_role(member.guild.id):
            role_id = self.role_service.get_role_for_guild(member.guild.id)
            if role_id:
                await self._remove_role_from_member(member, role_id)

    # New expandable reaction role system
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction additions for new reaction role system."""
        # Skip bot reactions
        if payload.member and payload.member.bot:
            return
        
        # Convert emoji to string format
        emoji_str = str(payload.emoji)
        
        # Check new reaction role system first
        role_id = self.role_service.get_reaction_role(payload.channel_id, emoji_str)
        
        if role_id:
            # Get the guild and member
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            member = await self._resolve_member(guild, payload.user_id,
                                                payload.member)
            if not member:
                return

            # Get the role
            role = guild.get_role(role_id)
            if not role:
                return

            # Check if member already has role
            if role in member.roles:
                return
            
            # Assign the role
            try:
                await member.add_roles(role)
            except discord.HTTPException:
                pass
            return
        
        # Fall back to legacy language role system if no new system match
        if self.role_service.is_reaction_role_channel(payload.channel_id):
            role_id = self.role_service.get_role_for_emoji(emoji_str)
            
            if role_id:
                guild = self.bot.get_guild(payload.guild_id)
                if not guild:
                    return
                
                member = await self._resolve_member(guild, payload.user_id,
                                                   payload.member)
                if not member:
                    return

                role = guild.get_role(role_id)
                if not role:
                    return

                try:
                    await member.add_roles(role)
                except discord.HTTPException:
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removals for new reaction role system."""
        # Convert emoji to string format
        emoji_str = str(payload.emoji)
        
        # Check new reaction role system first
        role_id = self.role_service.get_reaction_role(payload.channel_id, emoji_str)
        
        if role_id:
            # Get the guild
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            # Get the member (removals never carry payload.member)
            member = await self._resolve_member(guild, payload.user_id)
            if not member:
                return
            
            # Get the role
            role = guild.get_role(role_id)
            if not role:
                return
            
            # Remove the role
            try:
                await member.remove_roles(role)
            except discord.HTTPException:
                pass
            return
        
        # Fall back to legacy language role system if no new system match
        if self.role_service.is_reaction_role_channel(payload.channel_id):
            role_id = self.role_service.get_role_for_emoji(emoji_str)
            
            if role_id:
                guild = self.bot.get_guild(payload.guild_id)
                if not guild:
                    return
                
                member = await self._resolve_member(guild, payload.user_id)
                if not member:
                    return

                role = guild.get_role(role_id)
                if not role:
                    return

                try:
                    await member.remove_roles(role)
                except discord.HTTPException:
                    pass

    # Graduate role assignment
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle graduate role assignment when users post in specific threads."""
        if message.author.bot:
            return
        
        if isinstance(message.channel, discord.Thread):
            user_role_ids = [role.id for role in message.author.roles]
            graduate_role_id = self.role_service.should_assign_graduate_role(
                message.channel.id, user_role_ids
            )
            
            if graduate_role_id:
                role = message.guild.get_role(graduate_role_id)
                if role and role not in message.author.roles:
                    try:
                        await message.author.add_roles(role)
                    except discord.HTTPException:
                        pass

    # Self-serve cross-server role sync (no Guild Members intent needed)
    async def _membership(self, guild_id: int, user_id: int) -> Optional[bool]:
        """True/False if we can tell whether the user is in a guild; None if we can't."""
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return None  # bot isn't in that server: unknown, never a removal
        if guild.get_member(user_id) is not None:
            return True
        try:
            await guild.fetch_member(user_id)
            return True
        except discord.NotFound:
            return False
        except discord.HTTPException:
            return None

    async def sync_member_roles(self, interaction: discord.Interaction):
        """Bring the user's main-server language roles in line with their server memberships."""
        from config.settings import settings

        user_id = interaction.user.id
        now = time.monotonic()
        wait = ROLE_SYNC_COOLDOWN_SECONDS - (now - self._last_role_sync.get(user_id, -ROLE_SYNC_COOLDOWN_SECONDS))
        if wait > 0:
            await interaction.response.send_message(
                f"⏳ You just synced - try again in {int(wait) + 1}s.", ephemeral=True)
            return
        self._last_role_sync[user_id] = now

        await interaction.response.defer(ephemeral=True, thinking=True)
        main_guild = self.bot.get_guild(settings.MAIN_SERVER_ID)
        member = await self._resolve_member(main_guild, user_id) if main_guild else None
        if member is None:
            await interaction.followup.send("You need to be in the main Refold server for role sync.",
                                            ephemeral=True)
            return

        memberships = {guild_id: await self._membership(guild_id, user_id)
                       for guild_id in self.role_service.get_synced_guild_roles()}
        to_add, to_remove = self.role_service.plan_role_sync(memberships, {r.id for r in member.roles})

        added = [r for r in (main_guild.get_role(rid) for rid in to_add) if r]
        removed = [r for r in (main_guild.get_role(rid) for rid in to_remove) if r]
        try:
            if added:
                await member.add_roles(*added, reason="Self-serve language server role sync")
            if removed:
                await member.remove_roles(*removed, reason="Self-serve language server role sync")
        except discord.HTTPException:
            await interaction.followup.send("Failed to update your roles. Please try again later.",
                                            ephemeral=True)
            return

        if not added and not removed:
            await interaction.followup.send("✅ Your language roles are already up to date.", ephemeral=True)
            return
        lines = [f"➕ {r.name}" for r in added] + [f"➖ {r.name}" for r in removed]
        await interaction.followup.send("✅ Roles updated:\n" + "\n".join(lines), ephemeral=True)

    @app_commands.command(name='syncroles',
                          description='Update your main-server language roles from the servers you are in')
    async def syncroles(self, interaction: discord.Interaction):
        """Self-serve cross-server role sync."""
        await self.sync_member_roles(interaction)

    @app_commands.command(name='syncrolesbutton', description='Post a "Sync my roles" button')
    @app_commands.describe(channel='Channel to post the button in (default: this one)')
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def post_sync_button(self, interaction: discord.Interaction,
                               channel: Optional[discord.TextChannel] = None):
        """Post the persistent role-sync button."""
        target = channel or interaction.channel
        await target.send("🔄 **Joined a language server?** Press the button to get its role "
                          "in the main Refold server.", view=SyncRolesView(self))
        await interaction.response.send_message(f"✅ Posted the role-sync button in {target.mention}.",
                                                ephemeral=True)

    # Spanish Book Club toggle
    @app_commands.command(name='spanishbook', description='Toggle the Spanish Book Club role')
    async def toggle_spanish_book_club(self, interaction: discord.Interaction):
        """Toggle Spanish Book Club role."""
        guild_id, role_id = self.role_service.get_spanish_book_club_config()
        user_id = interaction.user.id

        spanish_guild = self.bot.get_guild(guild_id)
        if not spanish_guild:
            await interaction.response.send_message("Spanish server not found.", ephemeral=True)
            return

        # Membership is checked by fetching the one member, which needs no
        # privileged intent (guild.members is empty without Guild Members).
        spanish_member = await self._resolve_member(spanish_guild, user_id)
        spanish_members = {spanish_member.id} if spanish_member else set()

        if not self.role_service.can_toggle_spanish_book_club(user_id, spanish_members):
            await interaction.response.send_message(
                "You must be a member of the Spanish server to use this command.", ephemeral=True)
            return

        from config.settings import settings
        main_guild = self.bot.get_guild(settings.MAIN_SERVER_ID)
        if not main_guild:
            await interaction.response.send_message("Main server not found.", ephemeral=True)
            return

        role = main_guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("Spanish Book Club role not found.", ephemeral=True)
            return

        member = await self._resolve_member(main_guild, user_id)
        if not member:
            await interaction.response.send_message("You are not a member of the main server.",
                                                    ephemeral=True)
            return

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message("Spanish Book Club role removed.", ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.response.send_message("Spanish Book Club role added.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("Failed to toggle role. Please try again later.",
                                                    ephemeral=True)


async def setup(bot):
    """Required setup function for cog loading."""
    await bot.add_cog(Roles(bot))