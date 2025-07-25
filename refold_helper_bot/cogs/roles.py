"""
Roles cog for Refold Helper Bot.
Handles cross-server role sync, reaction roles, and special role features.
"""

import discord
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

    # Reaction role system
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction additions for roles and bookmarks."""
        if payload.user_id == self.bot.user.id:
            return  # Ignore bot's own reactions

        user = await self.bot.fetch_user(payload.user_id)
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        emoji = str(payload.emoji)

        # Delete bot's own DM message if ❌ is added
        if emoji == '❌' and isinstance(channel, discord.DMChannel) and message.author == self.bot.user:
            await message.delete()
            return

        # Bookmark reaction
        if emoji == '🔖':
            guild = await self.bot.fetch_guild(payload.guild_id)
            embed = discord.Embed(title='You made a bookmark!', description='', color=0xc91f16)
            embed.add_field(name='The message said:', value=f'{message.content}', inline=True)
            msg = await user.send(f'Click to view original message: https://discord.com/channels/{guild.id}/{channel.id}/{message.id}', embed=embed)
            await msg.add_reaction('❌')

        # Role reaction section
        if payload.guild_id and self.role_service.is_reaction_role_channel(payload.channel_id):
            guild = await self.bot.fetch_guild(payload.guild_id)
            member = await guild.fetch_member(payload.user_id)
            
            if self.role_service.is_valid_reaction_emoji(emoji):
                role_id = self.role_service.get_role_for_emoji(emoji)
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        await member.add_roles(role)
            else:
                await message.remove_reaction(emoji, user)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removals for role system."""
        if self.role_service.is_reaction_role_channel(payload.channel_id):
            guild = await self.bot.fetch_guild(payload.guild_id)
            member = await guild.fetch_member(payload.user_id)
            emoji = str(payload.emoji)
            
            if self.role_service.is_valid_reaction_emoji(emoji):
                role_id = self.role_service.get_role_for_emoji(emoji)
                if role_id:
                    role = guild.get_role(role_id)
                    if role:
                        await member.remove_roles(role)

    # Graduate role assignment
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle graduate role assignment when posting in Day 30 threads."""
        if message.channel.type == discord.ChannelType.public_thread:
            user_role_ids = [role.id for role in message.author.roles]
            graduate_role_id = self.role_service.should_assign_graduate_role(
                message.channel.id, user_role_ids
            )
            
            if graduate_role_id:
                role_to_add = message.guild.get_role(graduate_role_id)
                if role_to_add:
                    await message.author.add_roles(role_to_add)
                    print(f"Assigned role {role_to_add.name} to {message.author.name}")

    # Spanish Book Club role toggle
    @commands.command(help='Toggle your Spanish Book Club role. Requires membership in the Spanish server.', 
                     category='General Commands')
    async def spanishbookclub(self, ctx):
        """Toggle Spanish Book Club role for Spanish server members."""
        target_guild_id, role_id = self.role_service.get_spanish_book_club_config()

        target_guild = self.bot.get_guild(target_guild_id)
        if not target_guild:
            await ctx.send("An error occurred. Please try again later.")
            return

        # Get set of member IDs for validation
        guild_member_ids = {member.id for member in target_guild.members}
        
        if not self.role_service.can_toggle_spanish_book_club(ctx.author.id, guild_member_ids):
            await ctx.send("You must join the Spanish server to use this command.")
            return

        role = target_guild.get_role(role_id)
        if not role:
            await ctx.send("An error occurred. The role does not exist.")
            return

        member = target_guild.get_member(ctx.author.id)
        if not member:
            await ctx.send("You must join the Spanish server to use this command.")
            return

        try:
            if role in member.roles:
                await member.remove_roles(role)
                await ctx.send("The Spanish Book Club role has been removed.")
            else:
                await member.add_roles(role)
                await ctx.send("The Spanish Book Club role has been added.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to update your role: {e}")


async def setup(bot):
    """Add the Roles cog to the bot."""
    await bot.add_cog(Roles(bot))