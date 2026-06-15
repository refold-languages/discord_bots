"""
Honeypot cog for Refold Helper Bot.

Watches any channel named ``#spam-honeypot`` (see HONEYPOT_CHANNEL_NAME).
A real member never has a reason to post there because a moderator pins a
warning explaining the channel is a trap, so anyone who does post is almost
certainly a spam bot. Those posters are instantly banned and their last
6 hours of messages across the server are purged. Staff are exempt so they
can post the warning message itself.
"""

import discord
from discord.ext import commands

from services import HoneypotService, enforcement_state
from config.constants import HONEYPOT_LOG_CHANNEL_ID, ANTISPAM_TEST_REACTION_BAN
from utils import get_logger


class Honeypot(commands.Cog):
    """Instant-ban honeypot for spam/scam bots."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.honeypot')
        self.honeypot_service = HoneypotService()

    async def cog_load(self):
        """Initialize the honeypot service when the cog loads."""
        self.honeypot_service.initialize()
        enforcement_state.initialize()
        self.logger.info("honeypot_cog_loaded")

    def _has_staff_powers(self, member: discord.Member) -> bool:
        """True if the member has any moderator/admin-level permission."""
        perms = getattr(member, 'guild_permissions', None)
        if perms is None:
            # Not a cached Member (rare) - be safe and treat as staff so we
            # never ban someone we can't verify.
            return True
        return any((
            perms.administrator,
            perms.ban_members,
            perms.kick_members,
            perms.manage_messages,
            perms.manage_guild,
        ))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Ban non-staff members who post in a honeypot channel."""
        # Ignore DMs and non-standard/system messages.
        if message.guild is None:
            return
        if message.type not in (discord.MessageType.default,
                                 discord.MessageType.reply):
            return

        channel_name = getattr(message.channel, 'name', None)
        if not self.honeypot_service.is_honeypot_channel(channel_name):
            return

        author = message.author
        guild = message.guild

        # Bots (including this one) are always ignored, even in test mode, so
        # the pinned warning message never trips the honeypot.
        if bool(getattr(author, 'bot', False)):
            return

        # Staff and the owner are exempt from the ban. In test mode we still
        # flag them (reaction + [TEST] log only, never banned) so admins can
        # verify the honeypot without a separate account.
        is_staff = (author.id == guild.owner_id
                    or self._has_staff_powers(author))
        if is_staff and not enforcement_state.is_test_mode():
            return

        # Master kill switch: take no action when enforcement is disabled.
        if not enforcement_state.is_enabled():
            return

        record = self.honeypot_service.build_ban_record(
            user_id=author.id,
            user_name=str(author),
            guild_id=guild.id,
            guild_name=guild.name,
            channel_id=message.channel.id,
            channel_name=channel_name,
            message_content=message.content,
        )

        # Test mode: react + log instead of banning, so staff can verify safely.
        if enforcement_state.is_test_mode():
            try:
                await message.add_reaction(ANTISPAM_TEST_REACTION_BAN)
            except discord.HTTPException as e:
                self.logger.warning("honeypot_test_reaction_failed",
                                    error=str(e), error_type=type(e).__name__)
            self.logger.info("honeypot_test_mode_trigger",
                             user_id=author.id, guild_id=guild.id,
                             channel_id=message.channel.id)
            await self._post_log_embed(record, test_mode=True,
                                       fallback_channel=message.channel)
            return

        delete_seconds = self.honeypot_service.get_ban_delete_seconds()
        try:
            await guild.ban(
                author,
                reason="Spam honeypot: posted in #%s" % channel_name,
                delete_message_seconds=delete_seconds,
            )
        except discord.Forbidden:
            self.logger.error("honeypot_ban_forbidden",
                              user_id=author.id, guild_id=guild.id,
                              note="Bot lacks Ban Members permission or role hierarchy")
            return
        except discord.HTTPException as e:
            self.logger.error("honeypot_ban_failed",
                              user_id=author.id, guild_id=guild.id,
                              error=str(e), error_type=type(e).__name__)
            return

        # Banning auto-deletes the triggering message within the purge window,
        # but delete it explicitly too in case it falls outside the window.
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        self.honeypot_service.record_ban(record)
        self.logger.warning("honeypot_ban_executed",
                            user_id=author.id, user_name=str(author),
                            guild_id=guild.id, channel_id=message.channel.id)

        await self._post_log_embed(record)

    async def _post_log_embed(self, record: dict, test_mode: bool = False,
                              fallback_channel=None):
        """Post a human-readable ban record to the mod log channel, if set."""
        channel = (self.bot.get_channel(HONEYPOT_LOG_CHANNEL_ID)
                   if HONEYPOT_LOG_CHANNEL_ID else None)
        if channel is None:
            # In test mode fall back to the triggering channel so feedback is
            # visible even on a server without the configured mod-log channel.
            if fallback_channel is not None:
                channel = fallback_channel
            else:
                self.logger.error("honeypot_log_channel_not_found",
                                  channel_id=HONEYPOT_LOG_CHANNEL_ID)
                return

        embed = discord.Embed(
            title='🧪 [TEST] Honeypot — would ban' if test_mode else '🍯 Spam honeypot ban',
            description=('**Test mode — no action taken.** This user posted in the '
                         'honeypot and would have been banned.'
                         if test_mode else
                         'A user was auto-banned for posting in the honeypot channel.'),
            color=0x95A5A6 if test_mode else 0xE74C3C,
        )
        embed.add_field(name='User',
                        value=f"{record['user_name']} (`{record['user_id']}`)",
                        inline=False)
        embed.add_field(name='Channel',
                        value=f"#{record['channel_name']}", inline=True)
        embed.add_field(name='Messages purged',
                        value=f"Last {record['messages_purged_seconds'] // 3600}h",
                        inline=True)
        embed.add_field(name='Their message',
                        value=record['message_content'] or '*(no text content)*',
                        inline=False)
        embed.set_footer(text=f"{record['timestamp']} • reason: {record['reason']}")

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            self.logger.error("honeypot_log_send_failed",
                              error=str(e), error_type=type(e).__name__)

    @commands.command(name='honeypotlog',
                      help='Show the most recent spam honeypot bans.',
                      category='General Commands')
    @commands.has_permissions(ban_members=True)
    async def honeypot_log(self, ctx, count: int = 10):
        """List recent honeypot bans so staff can review who/why/when."""
        count = max(1, min(count, 25))
        records = self.honeypot_service.get_ban_records()

        if not records:
            await ctx.send("No honeypot bans recorded yet.")
            return

        recent = records[-count:][::-1]
        embed = discord.Embed(
            title='🍯 Recent spam honeypot bans',
            description=f"Showing {len(recent)} of {len(records)} total.",
            color=0xE74C3C,
        )
        for r in recent:
            embed.add_field(
                name=f"{r.get('user_name', 'unknown')} ({r.get('user_id')})",
                value=f"{r.get('timestamp', '?')} — #{r.get('channel_name', '?')}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @honeypot_log.error
    async def honeypot_log_error(self, ctx, error):
        """Quietly inform users who lack permission."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You need the Ban Members permission to use this.")


async def setup(bot):
    """Add the Honeypot cog to the bot."""
    await bot.add_cog(Honeypot(bot))
