"""
Roles cog for Refold Helper Bot.
Handles cross-server role sync, reaction roles, and special role features.
"""

import discord
from discord import app_commands
from discord.ext import commands

from services import RoleService


class Roles(commands.Cog):
    """Role management system for cross-server sync and reaction roles."""
    
    def __init__(self, bot):
        self.bot = bot
        self.role_service = RoleService()
    
    async def cog_load(self):
        """Initialize the role service when cog loads."""
        self.role_service.initialize()

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