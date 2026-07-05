"""
Anti-spam cog for Refold Helper Bot.

Behaviour-based spam detection that complements the honeypot. It watches every
message across the community servers, feeds plain values to the
``SpamDetectionService``, and carries out whatever escalating action the engine
recommends:

  * BAN     - high confidence (image flood, new-user word-filter hit, or a soft
              signal from a brand-new account). Mirrors the honeypot: ban +
              purge recent messages.
  * TIMEOUT - softer signals (cross-channel / rapid repeat, or a lone image
              dump: 2+ images with no text from a user with no recent activity)
              from an established member. 1-week timeout + delete the offending
              message, then ping the mod log so staff can confirm a ban if
              warranted.

Staff (anyone with mod/admin powers), the guild owner, and bots are exempt, so
this only ever fires on ordinary members behaving like spam bots.
"""

from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from services import (
    SpamDetectionService, ACTION_BAN, ACTION_TIMEOUT, ACTION_NONE,
    enforcement_state,
)
from config.constants import (
    ANTISPAM_LOG_CHANNEL_ID,
    ANTISPAM_TEST_REACTION_BAN,
    ANTISPAM_TEST_REACTION_TIMEOUT,
)
from utils import get_logger


class AntiSpam(commands.Cog):
    """Heuristic anti-spam enforcement."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.antispam')
        self.spam_service = SpamDetectionService()

    async def cog_load(self):
        """Initialize the spam detection service when the cog loads."""
        self.spam_service.initialize()
        enforcement_state.initialize()
        self.logger.info("antispam_cog_loaded")

    # ------------------------------------------------------------------
    # Helpers (turn Discord objects into plain values for the service)
    # ------------------------------------------------------------------
    def _has_staff_powers(self, member: discord.Member) -> bool:
        """True if the member has any moderator/admin-level permission."""
        perms = getattr(member, 'guild_permissions', None)
        if perms is None:
            # Not a cached Member - be safe and treat as staff so we never
            # action someone we can't verify.
            return True
        return any((
            perms.administrator,
            perms.ban_members,
            perms.kick_members,
            perms.manage_messages,
            perms.manage_guild,
        ))

    @staticmethod
    def _count_images(message: discord.Message) -> int:
        """Number of images carried by a message (attachments + image embeds)."""
        count = 0
        for att in message.attachments:
            ctype = (att.content_type or '')
            if ctype.startswith('image/') or _looks_like_image(att.filename):
                count += 1
        for embed in message.embeds:
            if embed.image or embed.thumbnail:
                count += 1
        return count

    @staticmethod
    def _age_days(dt) -> float:
        """Whole+fractional days between dt (aware UTC) and now."""
        now = datetime.now(timezone.utc)
        return (now - dt).total_seconds() / 86400.0

    @staticmethod
    def _minutes_since(dt) -> float:
        now = datetime.now(timezone.utc)
        return (now - dt).total_seconds() / 60.0

    # ------------------------------------------------------------------
    # Event listener
    # ------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Evaluate every member message and enforce the engine's decision."""
        # Ignore DMs and non-standard/system messages.
        if message.guild is None:
            return
        if message.type not in (discord.MessageType.default,
                                 discord.MessageType.reply):
            return
        if message.author.bot:
            return

        # Master kill switch: when disabled, take no action anywhere.
        if not enforcement_state.is_enabled():
            return

        guild = message.guild
        if not self.spam_service.is_enabled_for_guild(guild.id):
            return

        author = message.author

        # Staff and the owner are exempt from enforcement. In test mode we
        # still evaluate them (reaction + [TEST] log only, never enforced) so
        # admins can verify detection without a separate account.
        is_staff = author.id == guild.owner_id or self._has_staff_powers(author)
        if is_staff and not enforcement_state.is_test_mode():
            return

        # Compute plain values. joined_at / created_at can be None for
        # partially-cached members; pass None and let the service degrade.
        joined_minutes = (self._minutes_since(author.joined_at)
                          if getattr(author, 'joined_at', None) else None)
        account_days = (self._age_days(author.created_at)
                        if getattr(author, 'created_at', None) else None)

        decision = self.spam_service.evaluate(
            guild_id=guild.id,
            user_id=author.id,
            channel_id=message.channel.id,
            message_id=message.id,
            timestamp=message.created_at.timestamp(),
            image_count=self._count_images(message),
            content=message.content or '',
            account_age_days=account_days,
            joined_minutes_ago=joined_minutes,
        )

        action = decision['action']

        # Diagnostic: in test mode, log every evaluation so detection can be
        # verified from the console even where Discord feedback is unavailable.
        if enforcement_state.is_test_mode():
            self.logger.info(
                f"antispam_eval action={action} "
                f"detectors={decision['detectors']} "
                f"content_len={len(message.content or '')} "
                f"channel={message.channel.id}")

        if action == ACTION_NONE:
            return

        channel_name = getattr(message.channel, 'name', str(message.channel.id))
        record = self.spam_service.build_action_record(
            action=action,
            confidence=decision['confidence'],
            reasons=decision['reasons'],
            user_id=author.id,
            user_name=str(author),
            guild_id=guild.id,
            guild_name=guild.name,
            channel_id=message.channel.id,
            channel_name=channel_name,
            message_content=message.content,
        )

        # Test mode: react instead of enforcing, so staff can verify detection
        # without anyone being banned/timed out.
        if enforcement_state.is_test_mode():
            await self._handle_test_mode(message, record)
            self.logger.info("antispam_test_mode_trigger",
                             action=action, confidence=decision['confidence'],
                             user_id=author.id, guild_id=guild.id,
                             channel_id=message.channel.id,
                             reasons=decision['reasons'])
            return

        if action == ACTION_BAN:
            ok = await self._do_ban(guild, author, message, decision)
        else:
            ok = await self._do_timeout(guild, author, message, decision)

        if not ok:
            return

        self.spam_service.record_action(record)
        self.logger.warning("antispam_action_executed",
                            action=action, confidence=decision['confidence'],
                            user_id=author.id, user_name=str(author),
                            guild_id=guild.id, channel_id=message.channel.id,
                            reasons=decision['reasons'])
        await self._post_log_embed(record)

    # ------------------------------------------------------------------
    # Enforcement actions
    # ------------------------------------------------------------------
    async def _do_ban(self, guild, author, message, decision) -> bool:
        """Ban the user and purge recent messages. Returns True on success."""
        reason = "Anti-spam: " + " ".join(decision['reasons'])[:480]
        try:
            await guild.ban(
                author,
                reason=reason,
                delete_message_seconds=self.spam_service.get_ban_delete_seconds(),
            )
        except discord.Forbidden:
            self.logger.error("antispam_ban_forbidden",
                              user_id=author.id, guild_id=guild.id,
                              note="Bot lacks Ban Members permission or role hierarchy")
            return False
        except discord.HTTPException as e:
            self.logger.error("antispam_ban_failed",
                              user_id=author.id, guild_id=guild.id,
                              error=str(e), error_type=type(e).__name__)
            return False

        # The ban purges within the window; delete the trigger explicitly too.
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        return True

    async def _do_timeout(self, guild, author, message, decision) -> bool:
        """Timeout the user and delete the offending message."""
        duration = timedelta(seconds=self.spam_service.get_timeout_seconds())
        reason = "Anti-spam: " + " ".join(decision['reasons'])[:480]
        try:
            await author.timeout(duration, reason=reason)
        except discord.Forbidden:
            self.logger.error("antispam_timeout_forbidden",
                              user_id=author.id, guild_id=guild.id,
                              note="Bot lacks Moderate Members permission or role hierarchy")
            return False
        except discord.HTTPException as e:
            self.logger.error("antispam_timeout_failed",
                              user_id=author.id, guild_id=guild.id,
                              error=str(e), error_type=type(e).__name__)
            return False

        # Timeout has no built-in bulk delete, so remove the spam burst the
        # detector saw (across whatever channels it spanned), not just the
        # one triggering message.
        await self._purge_refs(decision.get('message_refs') or [(message.channel.id,
                                                                  message.id)])
        return True

    async def _purge_refs(self, refs):
        """Delete a list of (channel_id, message_id) spam messages."""
        deleted = 0
        for channel_id, message_id in refs:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                continue
            try:
                await channel.get_partial_message(message_id).delete()
                deleted += 1
            except discord.HTTPException:
                pass
        if deleted:
            self.logger.info("antispam_burst_purged", deleted=deleted,
                             attempted=len(refs))

    # ------------------------------------------------------------------
    # Test mode
    # ------------------------------------------------------------------
    async def _handle_test_mode(self, message: discord.Message, record: dict):
        """React to a message that WOULD be actioned, and log it (no enforcement)."""
        is_ban = record['action'] == ACTION_BAN
        emoji = ANTISPAM_TEST_REACTION_BAN if is_ban else ANTISPAM_TEST_REACTION_TIMEOUT
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException as e:
            self.logger.warning("antispam_test_reaction_failed",
                                error=str(e), error_type=type(e).__name__)
        # Fall back to the triggering channel so test mode is visible even on a
        # server without the configured mod-log channel (e.g. a test server).
        await self._post_log_embed(record, test_mode=True,
                                   fallback_channel=message.channel)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    async def _post_log_embed(self, record: dict, test_mode: bool = False,
                              fallback_channel=None):
        """Post a human-readable action record to the mod log channel, if set."""
        channel = (self.bot.get_channel(ANTISPAM_LOG_CHANNEL_ID)
                   if ANTISPAM_LOG_CHANNEL_ID else None)
        if channel is None:
            # In test mode, fall back to the triggering channel so feedback is
            # always visible; for real actions, just log the misconfiguration.
            if fallback_channel is not None:
                channel = fallback_channel
            else:
                self.logger.error("antispam_log_channel_not_found",
                                  channel_id=ANTISPAM_LOG_CHANNEL_ID)
                return

        is_ban = record['action'] == ACTION_BAN
        if test_mode:
            title = ('🧪 [TEST] Would ban' if is_ban else '🧪 [TEST] Would timeout')
            description = ('**Test mode — no action taken.** This user would have '
                           f"been {'banned' if is_ban else 'timed out'}.")
            color = 0x95A5A6
        else:
            title = '🚫 Anti-spam ban' if is_ban else '⏳ Anti-spam timeout'
            description = ('A user was auto-banned for spam-like behaviour.'
                           if is_ban else
                           'A user was timed out (1 week) for spam-like behaviour. '
                           '**Staff: confirm a ban if warranted.**')
            color = 0xE74C3C if is_ban else 0xF1C40F
        embed = discord.Embed(title=title, description=description, color=color)
        embed.add_field(name='User',
                        value=f"{record['user_name']} (`{record['user_id']}`)",
                        inline=False)
        embed.add_field(name='Channel', value=f"#{record['channel_name']}",
                        inline=True)
        embed.add_field(name='Confidence',
                        value=str(record.get('confidence') or 'n/a'),
                        inline=True)
        embed.add_field(name='Why',
                        value="\n".join(f"• {r}" for r in record['reasons'])
                              or '*(no detail)*',
                        inline=False)
        embed.add_field(name='Their message',
                        value=record['message_content'] or '*(no text content)*',
                        inline=False)
        embed.set_footer(text=record['timestamp'])

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            self.logger.error("antispam_log_send_failed",
                              error=str(e), error_type=type(e).__name__)

    # ------------------------------------------------------------------
    # Staff commands
    # ------------------------------------------------------------------
    @commands.command(name='spamstats',
                      help='Show the most recent automatic anti-spam actions.',
                      category='General Commands')
    @commands.has_permissions(ban_members=True)
    async def spam_stats(self, ctx, count: int = 10):
        """List recent anti-spam actions so staff can review who/why/when."""
        count = max(1, min(count, 25))
        records = self.spam_service.get_action_records()

        if not records:
            await ctx.send("No anti-spam actions recorded yet.")
            return

        recent = records[-count:][::-1]
        embed = discord.Embed(
            title='🛡️ Recent anti-spam actions',
            description=f"Showing {len(recent)} of {len(records)} total.",
            color=0x3498DB,
        )
        for r in recent:
            why = "; ".join(r.get('reasons', [])) or '?'
            embed.add_field(
                name=f"[{r.get('action', '?')}] {r.get('user_name', 'unknown')} "
                     f"({r.get('user_id')})",
                value=f"{r.get('timestamp', '?')} — #{r.get('channel_name', '?')}\n{why}"[:1024],
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(name='antispam',
                      help='Toggle anti-spam for this server: !antispam on|off',
                      category='General Commands')
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def antispam_toggle(self, ctx, state: str = ''):
        """Enable or disable heuristic anti-spam in the current guild."""
        state = state.strip().lower()
        if state not in ('on', 'off'):
            enabled = self.spam_service.is_enabled_for_guild(ctx.guild.id)
            await ctx.send(
                f"Anti-spam is currently **{'on' if enabled else 'off'}** here. "
                f"Use `!antispam on` or `!antispam off` to change it."
            )
            return

        enabled = state == 'on'
        if self.spam_service.set_guild_enabled(ctx.guild.id, enabled):
            self.logger.info("antispam_toggled", guild_id=ctx.guild.id,
                             enabled=enabled, by_user=ctx.author.id)
            await ctx.send(f"Anti-spam is now **{state}** for this server.")
        else:
            await ctx.send("Failed to save the setting — check the logs.")

    # --- Global kill switch + test mode (covers honeypot too) ----------
    @commands.group(name='moderation', invoke_without_command=True,
                    help='Master control for all spam/ban enforcement. '
                         'Subcommands: status, enable, disable, testmode on|off',
                    category='General Commands')
    @commands.has_permissions(manage_guild=True)
    async def moderation(self, ctx):
        """Show the current global enforcement state."""
        await self._send_mod_status(ctx)

    @moderation.command(name='status', help='Show the enforcement state.')
    @commands.has_permissions(manage_guild=True)
    async def moderation_status(self, ctx):
        await self._send_mod_status(ctx)

    @moderation.command(name='disable',
                        help='EMERGENCY: turn OFF all automatic bans/timeouts.')
    @commands.has_permissions(manage_guild=True)
    async def moderation_disable(self, ctx):
        enforcement_state.set_enabled(False)
        self.logger.warning("moderation_emergency_disabled", by_user=ctx.author.id)
        await ctx.send("🛑 **EMERGENCY STOP.** All automatic spam/ban enforcement "
                       "is now OFF (anti-spam **and** honeypot). Re-enable with "
                       "`!moderation enable`.")

    @moderation.command(name='enable',
                        help='Turn automatic bans/timeouts back ON.')
    @commands.has_permissions(manage_guild=True)
    async def moderation_enable(self, ctx):
        enforcement_state.set_enabled(True)
        self.logger.warning("moderation_re_enabled", by_user=ctx.author.id)
        await ctx.send("✅ Automatic spam/ban enforcement is now **ON**.")

    @moderation.command(name='testmode',
                        help='Detect-only mode: react instead of acting. '
                             'Usage: !moderation testmode on|off')
    @commands.has_permissions(manage_guild=True)
    async def moderation_testmode(self, ctx, state: str = ''):
        state = state.strip().lower()
        if state not in ('on', 'off'):
            await self._send_mod_status(ctx)
            return
        enforcement_state.set_test_mode(state == 'on')
        self.logger.warning("moderation_test_mode_set",
                            test_mode=(state == 'on'), by_user=ctx.author.id)
        if state == 'on':
            await ctx.send(
                f"🧪 **Test mode ON.** No one will be banned, timed out, or have "
                f"messages deleted. Triggering messages get a {ANTISPAM_TEST_REACTION_BAN}"
                f"/{ANTISPAM_TEST_REACTION_TIMEOUT} reaction and a `[TEST]` mod-log entry. "
                f"Applies to anti-spam and the honeypot — **staff included while testing**, "
                f"so you can verify it yourself.")
        else:
            await ctx.send("✅ **Test mode OFF.** Enforcement is live again.")

    async def _send_mod_status(self, ctx):
        """Report the global enforcement + test-mode state."""
        snap = enforcement_state.snapshot()
        guild_on = (ctx.guild is not None
                    and self.spam_service.is_enabled_for_guild(ctx.guild.id))
        embed = discord.Embed(
            title='🛡️ Moderation enforcement status',
            color=0x2ECC71 if snap['enabled'] else 0xE74C3C,
        )
        embed.add_field(name='Global enforcement',
                        value='🟢 ON' if snap['enabled'] else '🔴 OFF (kill switch)',
                        inline=True)
        embed.add_field(name='Test mode',
                        value='🧪 ON (detect-only)' if snap['test_mode'] else 'off',
                        inline=True)
        if ctx.guild is not None:
            embed.add_field(name='Anti-spam (this server)',
                            value='on' if guild_on else 'off', inline=True)
        await ctx.send(embed=embed)

    @spam_stats.error
    @antispam_toggle.error
    @moderation.error
    @moderation_status.error
    @moderation_enable.error
    @moderation_disable.error
    @moderation_testmode.error
    async def _perm_error(self, ctx, error):
        """Quietly inform users who lack permission."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")


def _looks_like_image(filename: str) -> bool:
    """Fallback image check by extension when content_type is missing."""
    if not filename:
        return False
    lower = filename.lower()
    return lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))


async def setup(bot):
    """Add the AntiSpam cog to the bot."""
    await bot.add_cog(AntiSpam(bot))
