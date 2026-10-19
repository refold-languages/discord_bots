"""
Anti-spam cog for Refold Helper Bot.

Without the Message Content intent (Discord denied it) messages arrive with no
text, attachments or embeds. The cog therefore works in two halves:

  * Content: the scam-link word filter runs as Discord AutoMod rules, which
    scan text server-side. ``/automod setup`` installs them per server, and
    ``on_automod_action`` applies the ban policy below to their hits.
  * Behaviour: ``on_message`` still sees who posted where and when, so the
    engine runs in content-free mode (channel hopping, @everyone pings).

When content *is* available, the full engine below runs as it always did.

Behaviour-based spam detection that complements the honeypot. It watches every
message across the community servers, feeds plain values to the
``SpamDetectionService``, and carries out whatever escalating action the engine
recommends:

  * BAN     - reserved for the near-certain cases only: a scam link or a real
              @everyone/@here ping from a member who joined minutes ago, or the
              same text spammed across channels by a brand-new account.
              Mirrors the honeypot: ban + purge recent messages.
  * TIMEOUT - the soft "not 100% sure" tier. Image dumps (which never ban) and
              anything else that merely looks off: remove the offending
              message(s), apply a SHORT timeout (a few minutes), and DM the
              user explaining what happened and how to post safely. Then ping
              the mod log — with the actual image links — so staff can confirm
              a ban if it really was a scammer.

Established members (they hold a role, have posted real text, or have been
around a while) are never banned or timed out for image behaviour. Staff,
the guild owner, and bots are exempt entirely, so this only ever fires on
ordinary members behaving like spam bots.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from services import (
    SpamDetectionService, ACTION_BAN, ACTION_TIMEOUT, ACTION_NONE,
    enforcement_state,
)
from services.automod_service import AutoModService
from config.constants import (
    ANTISPAM_LOG_CHANNEL_ID,
    ANTISPAM_TEST_REACTION_BAN,
    ANTISPAM_TEST_REACTION_TIMEOUT,
    ANTISPAM_SOFT_DM_MESSAGE,
)
from utils import get_logger


class AntiSpam(commands.Cog):
    """Heuristic anti-spam enforcement."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.antispam')
        self.spam_service = SpamDetectionService()
        self.automod_service = AutoModService()
        # AutoMod rule id -> name, so executions can be matched to our rules.
        self._automod_rule_names: Dict[int, Optional[str]] = {}

    @property
    def content_available(self) -> bool:
        """Whether messages arrive with their text, attachments and embeds."""
        return self.bot.intents.message_content

    async def cog_load(self):
        """Initialize the spam detection service when the cog loads."""
        self.spam_service.initialize()
        self.automod_service.initialize()
        enforcement_state.initialize()
        self.prune_records.start()
        self.logger.info("antispam_cog_loaded",
                         content_available=self.content_available)

    async def cog_unload(self):
        self.prune_records.cancel()

    @tasks.loop(hours=24)
    async def prune_records(self):
        """Apply the moderation-record retention policy once a day."""
        self.spam_service.prune_action_records()

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
    def _image_urls(message: discord.Message) -> list:
        """Direct links to a message's images, so mods can review them in-log."""
        urls = []
        for att in message.attachments:
            ctype = (att.content_type or '')
            if ctype.startswith('image/') or _looks_like_image(att.filename):
                urls.append(att.url)
        for embed in message.embeds:
            if embed.image and embed.image.url:
                urls.append(embed.image.url)
            elif embed.thumbnail and embed.thumbnail.url:
                urls.append(embed.thumbnail.url)
        return urls

    @staticmethod
    def _has_roles(member: discord.Member) -> bool:
        """True if the member holds any role beyond @everyone (self-assigned).

        A real presence signal: in the Refold servers members pick language
        roles, so anyone role-bearing is treated as an established member and
        spared image-dump enforcement.
        """
        roles = getattr(member, 'roles', None)
        if not roles:
            return False
        # roles always includes @everyone; anything more means a real role.
        return len(roles) > 1

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
            has_roles=self._has_roles(author),
            mentions_everyone=message.mention_everyone,
            content_available=self.content_available,
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
            image_urls=self._image_urls(message),
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

    @commands.Cog.listener()
    async def on_automod_action(self, execution: discord.AutoModAction):
        """Escalate scam-filter AutoMod hits from brand-new members to a ban.

        AutoMod reports who triggered which rule where, but not the message
        text (that needs the Message Content intent); the matched pattern is
        enough to apply the same new-member policy the word filter had.
        """
        # Discord sends one execution per action on the rule; the scam rule
        # only alerts, so act on that one event.
        if execution.action.type is not discord.AutoModRuleActionType.send_alert_message:
            return
        if execution.rule_trigger_type is not discord.AutoModRuleTriggerType.keyword:
            return

        guild = execution.guild
        if guild is None or not self.spam_service.is_enabled_for_guild(guild.id):
            return
        if not enforcement_state.is_enabled():
            return
        if not self.automod_service.is_escalating_rule(await self._automod_rule_name(execution)):
            return

        author = execution.member
        if author is None:
            try:
                author = await guild.fetch_member(execution.user_id)
            except discord.HTTPException:
                return  # already gone (left or banned)
        if author.bot:
            return
        is_staff = author.id == guild.owner_id or self._has_staff_powers(author)
        if is_staff and not enforcement_state.is_test_mode():
            return

        joined_minutes = (self._minutes_since(author.joined_at)
                          if getattr(author, 'joined_at', None) else None)
        decision = self.spam_service.evaluate_automod_hit(
            matched_keyword=execution.matched_keyword,
            joined_minutes_ago=joined_minutes,
        )
        if decision['action'] == ACTION_NONE:
            return

        channel = guild.get_channel_or_thread(execution.channel_id) if execution.channel_id else None
        message = (channel.get_partial_message(execution.message_id)
                   if channel is not None and execution.message_id else None)
        record = self.spam_service.build_action_record(
            action=decision['action'],
            confidence=decision['confidence'],
            reasons=decision['reasons'],
            user_id=author.id,
            user_name=str(author),
            guild_id=guild.id,
            guild_name=guild.name,
            channel_id=execution.channel_id,
            channel_name=getattr(channel, 'name', str(execution.channel_id)),
            message_content=execution.content,
        )

        if enforcement_state.is_test_mode():
            if message is not None:
                await self._handle_test_mode(message, record, fallback_channel=channel)
            else:
                await self._post_log_embed(record, test_mode=True, fallback_channel=channel)
            self.logger.info("antispam_automod_test_mode_trigger",
                             user_id=author.id, guild_id=guild.id,
                             reasons=decision['reasons'])
            return

        if not await self._do_ban(guild, author, message, decision):
            return
        self.spam_service.record_action(record)
        self.logger.warning("antispam_action_executed", source="automod",
                            action=decision['action'], user_id=author.id,
                            user_name=str(author), guild_id=guild.id,
                            channel_id=execution.channel_id,
                            reasons=decision['reasons'])
        await self._post_log_embed(record)

    async def _automod_rule_name(self, execution: discord.AutoModAction) -> Optional[str]:
        """Name of the rule behind an execution, cached per rule id."""
        if execution.rule_id not in self._automod_rule_names:
            try:
                rule = await execution.fetch_rule()
                self._automod_rule_names[execution.rule_id] = rule.name
            except discord.HTTPException as e:
                self.logger.warning("automod_rule_fetch_failed", rule_id=execution.rule_id,
                                    error=str(e), error_type=type(e).__name__)
                return None
        return self._automod_rule_names[execution.rule_id]

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
        if message is not None:
            try:
                await message.delete()
            except discord.HTTPException:
                pass
        return True

    async def _do_timeout(self, guild, author, message, decision) -> bool:
        """Soft action: brief timeout, remove the burst, and DM the user.

        This is the "not 100% sure" path. It is deliberately gentle so that a
        wrongly-flagged member loses a message and a few minutes, not their
        account, and is told exactly how to avoid it next time.
        """
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
        # Let the (possibly innocent) user know what happened and how to fix it.
        await self._send_soft_dm(author)
        return True

    async def _send_soft_dm(self, author) -> None:
        """DM a soft-actioned user. Best-effort: many members have DMs closed."""
        minutes = max(1, self.spam_service.get_timeout_seconds() // 60)
        try:
            await author.send(ANTISPAM_SOFT_DM_MESSAGE.format(minutes=minutes))
        except (discord.Forbidden, discord.HTTPException) as e:
            self.logger.info("antispam_soft_dm_failed",
                             user_id=getattr(author, 'id', None),
                             error=str(e), error_type=type(e).__name__)

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
    async def _handle_test_mode(self, message, record: dict, fallback_channel=None):
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
                                   fallback_channel=fallback_channel or message.channel)

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
                           'A user was briefly timed out (a few minutes) and DMed '
                           'because their message looked spammy but was **not** a '
                           'sure thing. Their message was removed. '
                           '**Staff: check the images below and ban only if this '
                           'really is a scammer.**')
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
                        value=record['message_content'] or (
                            '*(no text content)*' if self.content_available
                            else '*(message text unavailable to the bot — see the AutoMod alert)*'),
                        inline=False)

        # Show the actual images so mods can eyeball whether this was a scammer
        # or a regular member sharing screenshots. First image is previewed;
        # all links are listed (Discord field cap is 1024 chars).
        image_urls = record.get('image_urls') or []
        if image_urls:
            listed = "\n".join(image_urls)
            if len(listed) > 1000:
                listed = listed[:1000] + f"\n… (+{len(image_urls)} total)"
            embed.add_field(name=f'Images ({len(image_urls)})', value=listed,
                            inline=False)
            embed.set_image(url=image_urls[0])

        embed.set_footer(text=record['timestamp'])

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            self.logger.error("antispam_log_send_failed",
                              error=str(e), error_type=type(e).__name__)

    # ------------------------------------------------------------------
    # Staff commands
    # ------------------------------------------------------------------
    @app_commands.command(name='spamstats', description='Show the most recent automatic anti-spam actions')
    @app_commands.describe(count='How many actions to show (1-25)')
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def spam_stats(self, interaction: discord.Interaction,
                         count: app_commands.Range[int, 1, 25] = 10):
        """List recent anti-spam actions so staff can review who/why/when."""
        records = self.spam_service.get_action_records()

        if not records:
            await interaction.response.send_message("No anti-spam actions recorded yet.", ephemeral=True)
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
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='antispam', description='Show or toggle anti-spam for this server')
    @app_commands.describe(state='Turn anti-spam on or off (omit to see the current state)')
    @app_commands.choices(state=[app_commands.Choice(name='on', value='on'),
                                 app_commands.Choice(name='off', value='off')])
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def antispam_toggle(self, interaction: discord.Interaction,
                              state: Optional[app_commands.Choice[str]] = None):
        """Enable or disable heuristic anti-spam in the current guild."""
        if state is None:
            enabled = self.spam_service.is_enabled_for_guild(interaction.guild_id)
            await interaction.response.send_message(
                f"Anti-spam is currently **{'on' if enabled else 'off'}** here. "
                f"Use `/antispam state:on` or `/antispam state:off` to change it.",
                ephemeral=True
            )
            return

        enabled = state.value == 'on'
        if self.spam_service.set_guild_enabled(interaction.guild_id, enabled):
            self.logger.info("antispam_toggled", guild_id=interaction.guild_id,
                             enabled=enabled, by_user=interaction.user.id)
            await interaction.response.send_message(f"Anti-spam is now **{state.value}** for this server.")
        else:
            await interaction.response.send_message("Failed to save the setting — check the logs.",
                                                    ephemeral=True)

    # --- Discord AutoMod rules ----------------------------------------
    automod = app_commands.Group(
        name='automod', description="Discord AutoMod rules managed by this bot",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @automod.command(name='setup', description="Install or update this bot's AutoMod rules here")
    @app_commands.describe(alert_channel='Staff channel where AutoMod posts its alerts')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_setup(self, interaction: discord.Interaction, alert_channel: discord.TextChannel):
        """Create/update the bot-managed AutoMod rules in this server."""
        guild = interaction.guild
        if not guild.me.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ I need the **Manage Server** permission to manage AutoMod rules.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        existing_rules = await guild.fetch_automod_rules()
        existing = [(r.id, r.name, r.trigger.type.value) for r in existing_rules]
        specs = self.automod_service.build_rule_specs(alert_channel.id)
        steps = self.automod_service.plan_reconciliation(existing, specs)

        lines = []
        reason = f"Refold Helper /automod setup by {interaction.user}"
        for op, rule_id, spec, note in steps:
            try:
                if op == 'create':
                    rule = await guild.create_automod_rule(
                        name=spec['name'],
                        event_type=discord.AutoModRuleEventType.message_send,
                        trigger=self._to_trigger(spec),
                        actions=self._to_actions(spec),
                        enabled=True,
                        reason=reason,
                    )
                    self._automod_rule_names[rule.id] = rule.name
                    lines.append(f"✅ Created **{spec['name']}**")
                elif op == 'update':
                    rule = await guild.fetch_automod_rule(rule_id)
                    await rule.edit(trigger=self._to_trigger(spec), actions=self._to_actions(spec),
                                    enabled=True, reason=reason)
                    self._automod_rule_names[rule_id] = spec['name']
                    lines.append(f"🔄 Updated **{spec['name']}**")
                else:
                    lines.append(f"⏭️ Skipped **{spec['name']}** — {note}")
            except discord.HTTPException as e:
                self.logger.error("automod_rule_apply_failed", guild_id=guild.id, op=op,
                                  rule=spec['name'], error=str(e), error_type=type(e).__name__)
                lines.append(f"❌ Failed to {op} **{spec['name']}**: {e.text or e}")

        self.logger.info("automod_setup_completed", guild_id=guild.id, by_user=interaction.user.id,
                         steps=[(op, spec['name']) for op, _, spec, _ in steps])
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @automod.command(name='status', description="Show this bot's AutoMod rules in this server")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automod_status(self, interaction: discord.Interaction):
        """List the bot-managed AutoMod rules and whether they are enabled."""
        guild = interaction.guild
        if not guild.me.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ I need the **Manage Server** permission to read AutoMod rules.", ephemeral=True)
            return
        rules = await guild.fetch_automod_rules()
        expected = [spec['name'] for spec in self.automod_service.build_rule_specs(0)]
        by_name = {r.name: r for r in rules}
        lines = []
        for name in expected:
            rule = by_name.get(name)
            if rule is None:
                lines.append(f"⚪ **{name}** — not installed")
            else:
                lines.append(f"{'🟢' if rule.enabled else '🔴'} **{name}** — "
                             f"{'enabled' if rule.enabled else 'disabled'}")
        lines.append("\nRun `/automod setup` to install or update them.")
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @staticmethod
    def _to_trigger(spec: dict) -> discord.AutoModTrigger:
        return discord.AutoModTrigger(type=discord.AutoModRuleTriggerType(spec['trigger_type']),
                                      **spec['trigger'])

    @staticmethod
    def _to_actions(spec: dict) -> list:
        return [discord.AutoModRuleAction(type=discord.AutoModRuleActionType(a['type']),
                                          channel_id=a.get('channel_id'),
                                          custom_message=a.get('custom_message'))
                for a in spec['actions']]

    # --- Global kill switch + test mode (covers honeypot too) ----------
    moderation = app_commands.Group(
        name='moderation',
        description='Master control for all automatic spam/ban enforcement',
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @moderation.command(name='status', description='Show the enforcement state')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def moderation_status(self, interaction: discord.Interaction):
        await self._send_mod_status(interaction)

    @moderation.command(name='disable', description='EMERGENCY: turn OFF all automatic bans/timeouts')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def moderation_disable(self, interaction: discord.Interaction):
        enforcement_state.set_enabled(False)
        self.logger.warning("moderation_emergency_disabled", by_user=interaction.user.id)
        await interaction.response.send_message(
            "🛑 **EMERGENCY STOP.** All automatic spam/ban enforcement "
            "is now OFF (anti-spam **and** honeypot). Re-enable with "
            "`/moderation enable`.")

    @moderation.command(name='enable', description='Turn automatic bans/timeouts back ON')
    @app_commands.checks.has_permissions(manage_guild=True)
    async def moderation_enable(self, interaction: discord.Interaction):
        enforcement_state.set_enabled(True)
        self.logger.warning("moderation_re_enabled", by_user=interaction.user.id)
        await interaction.response.send_message("✅ Automatic spam/ban enforcement is now **ON**.")

    @moderation.command(name='testmode', description='Detect-only mode: react instead of acting')
    @app_commands.describe(state='Turn test mode on or off (omit to see the current state)')
    @app_commands.choices(state=[app_commands.Choice(name='on', value='on'),
                                 app_commands.Choice(name='off', value='off')])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def moderation_testmode(self, interaction: discord.Interaction,
                                  state: Optional[app_commands.Choice[str]] = None):
        if state is None:
            await self._send_mod_status(interaction)
            return
        enforcement_state.set_test_mode(state.value == 'on')
        self.logger.warning("moderation_test_mode_set",
                            test_mode=(state.value == 'on'), by_user=interaction.user.id)
        if state.value == 'on':
            await interaction.response.send_message(
                f"🧪 **Test mode ON.** No one will be banned, timed out, or have "
                f"messages deleted. Triggering messages get a {ANTISPAM_TEST_REACTION_BAN}"
                f"/{ANTISPAM_TEST_REACTION_TIMEOUT} reaction and a `[TEST]` mod-log entry. "
                f"Applies to anti-spam and the honeypot — **staff included while testing**, "
                f"so you can verify it yourself.")
        else:
            await interaction.response.send_message("✅ **Test mode OFF.** Enforcement is live again.")

    async def _send_mod_status(self, interaction: discord.Interaction):
        """Report the global enforcement + test-mode state."""
        snap = enforcement_state.snapshot()
        guild_on = (interaction.guild_id is not None
                    and self.spam_service.is_enabled_for_guild(interaction.guild_id))
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
        if interaction.guild_id is not None:
            embed.add_field(name='Anti-spam (this server)',
                            value='on' if guild_on else 'off', inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


def _looks_like_image(filename: str) -> bool:
    """Fallback image check by extension when content_type is missing."""
    if not filename:
        return False
    lower = filename.lower()
    return lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))


async def setup(bot):
    """Add the AntiSpam cog to the bot."""
    await bot.add_cog(AntiSpam(bot))
