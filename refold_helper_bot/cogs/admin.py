"""
Admin cog for Refold Helper Bot.
Contains administrative commands for analytics and bot management.
"""

from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from config.constants import COMMUNITY_SERVERS, ALLOWED_ADMIN_USER_IDS


def bot_admins_only():
    """Restrict a slash command to the users in ALLOWED_ADMIN_USER_IDS."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id not in ALLOWED_ADMIN_USER_IDS:
            raise app_commands.CheckFailure("You don't have permission to use this command.")
        return True
    return app_commands.check(predicate)


class Admin(commands.Cog):
    """Administrative commands for bot management and analytics."""

    def __init__(self, bot):
        self.bot = bot

    async def _cog_autocomplete(self, current: str) -> List[app_commands.Choice[str]]:
        from cogs import COGS
        names = [cog.split('.')[-1] for cog in COGS]
        return [app_commands.Choice(name=n, value=n) for n in names if current.lower() in n][:25]

    @app_commands.command(description='Checks the ping of the bot.')
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency."""
        await interaction.response.send_message(
            f'Pong! The bot\'s latency is {round(self.bot.latency * 1000)}ms')

    @app_commands.command(description="Reload a cog, or 'all' of them")
    @app_commands.describe(cog_name="Cog to reload, or 'all'")
    @app_commands.default_permissions(administrator=True)
    @bot_admins_only()
    async def reload(self, interaction: discord.Interaction, cog_name: str):
        """Reload a cog. Use 'all' to reload all cogs."""
        if cog_name == "all":
            # Reload all cogs
            from cogs import COGS
            reloaded = []
            failed = []

            for cog in COGS:
                if cog not in self.bot.extensions:
                    continue  # deliberately skipped at startup (missing intent)
                try:
                    await self.bot.reload_extension(cog)
                    reloaded.append(cog)
                except Exception as e:
                    failed.append(f"{cog}: {str(e)}")

            embed = discord.Embed(title="Reload All Results", color=0x00ff00 if not failed else 0xff9900)
            if reloaded:
                embed.add_field(name="✅ Reloaded", value="\n".join(reloaded), inline=False)
            if failed:
                embed.add_field(name="❌ Failed", value="\n".join(failed)[:1024], inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await self.bot.reload_extension(f"cogs.{cog_name}")
            await interaction.response.send_message(f"✅ Reloaded `cogs.{cog_name}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to reload `cogs.{cog_name}`: {str(e)}",
                                                    ephemeral=True)

    @reload.autocomplete('cog_name')
    async def _reload_autocomplete(self, interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name='all', value='all')] + (await self._cog_autocomplete(current))[:24]

    @app_commands.command(description='Unload a cog')
    @app_commands.describe(cog_name='Cog to unload')
    @app_commands.default_permissions(administrator=True)
    @bot_admins_only()
    async def unload(self, interaction: discord.Interaction, cog_name: str):
        """Unload a cog."""
        try:
            await self.bot.unload_extension(f"cogs.{cog_name}")
            await interaction.response.send_message(f"✅ Unloaded `cogs.{cog_name}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to unload `cogs.{cog_name}`: {str(e)}",
                                                    ephemeral=True)

    @app_commands.command(description='Load a cog')
    @app_commands.describe(cog_name='Cog to load')
    @app_commands.default_permissions(administrator=True)
    @bot_admins_only()
    async def load(self, interaction: discord.Interaction, cog_name: str):
        """Load a cog."""
        try:
            await self.bot.load_extension(f"cogs.{cog_name}")
            await interaction.response.send_message(f"✅ Loaded `cogs.{cog_name}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to load `cogs.{cog_name}`: {str(e)}",
                                                    ephemeral=True)

    @unload.autocomplete('cog_name')
    @load.autocomplete('cog_name')
    async def _load_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._cog_autocomplete(current)

    @app_commands.command(description='Push slash-command changes to Discord now')
    @app_commands.describe(force='Sync even if the command definitions look unchanged')
    @app_commands.default_permissions(administrator=True)
    @bot_admins_only()
    async def sync(self, interaction: discord.Interaction, force: bool = False):
        """Sync the slash-command tree (startup already does this when it changes)."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        synced = await self.bot.sync_commands_if_changed(force=force)
        await interaction.followup.send(
            "✅ Slash commands synced." if synced else "ℹ️ No changes to sync (use `force` to sync anyway).",
            ephemeral=True)

    @app_commands.command(description='Approximate member counts across the community servers')
    @app_commands.default_permissions(administrator=True)
    @bot_admins_only()
    async def membercounts(self, interaction: discord.Interaction):
        """Report approximate member counts per community server.

        Exact unique-user counts need the full member list, which requires the
        Guild Members intent; Discord's approximate counts need no intent.
        """
        await interaction.response.defer(ephemeral=True, thinking=True)

        lines = []
        total = 0
        for guild_id in COMMUNITY_SERVERS:
            try:
                guild = await self.bot.fetch_guild(guild_id, with_counts=True)
            except discord.HTTPException:
                lines.append(f"• `{guild_id}`: unavailable")
                continue
            count = guild.approximate_member_count or 0
            total += count
            lines.append(f"• {guild.name}: ~{count:,}")

        embed = discord.Embed(title="Community member counts (approximate)", color=0x3498DB,
                              description="\n".join(lines)[:4000])
        embed.set_footer(text=f"Sum: ~{total:,} (people in several servers are counted more than once)")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    """Add the Admin cog to the bot."""
    await bot.add_cog(Admin(bot))
