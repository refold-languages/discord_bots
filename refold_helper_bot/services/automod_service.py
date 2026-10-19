"""
AutoMod service for Refold Helper Bot.

Discord denied the Message Content intent, so the bot can no longer read what
members post. Discord's own AutoMod still can: it scans content server-side
and tells the bot *that* a rule fired (user, channel, matched pattern) without
the bot ever needing the message text. This service describes the AutoMod
rules the bot manages and works out how to bring a guild in line with them.

Like the other services it is free of Discord API calls: rule specs are plain
dicts, and reconciliation takes plain (id, name, trigger type) tuples. The cog
turns specs into discord.py objects and performs the API calls.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .base_service import BaseService
from config.constants import (
    ANTISPAM_WORD_FILTER_PATTERNS,
    AUTOMOD_RULE_PREFIX,
    AUTOMOD_MENTION_LIMIT,
    AUTOMOD_BLOCK_MESSAGE,
)
from utils import get_logger


# Discord AutoMod trigger types (mirrors discord.AutoModRuleTriggerType).
TRIGGER_KEYWORD = 1
TRIGGER_SPAM = 3
TRIGGER_MENTION_SPAM = 5

# Discord AutoMod action types (mirrors discord.AutoModRuleActionType).
ACTION_BLOCK_MESSAGE = 1
ACTION_SEND_ALERT = 2

# Discord limits for keyword rules.
MAX_REGEX_PER_RULE = 10
MAX_REGEX_LENGTH = 260

# Trigger types Discord allows only one rule of per guild. If a server's
# admins already configured one themselves, we leave theirs alone.
SINGLETON_TRIGGERS = {TRIGGER_SPAM, TRIGGER_MENTION_SPAM}

SCAM_RULE_NAME = f"{AUTOMOD_RULE_PREFIX} scam links"


class AutoModService(BaseService):
    """Describes the bot-managed AutoMod rules and plans their reconciliation."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.automod')

    # ------------------------------------------------------------------
    # Rule specs
    # ------------------------------------------------------------------
    @staticmethod
    def scam_regex_patterns() -> List[str]:
        """The anti-spam word filter as case-insensitive AutoMod regexes.

        AutoMod uses Rust-flavoured regex; the inline ``(?i)`` flag keeps the
        old engine's case-insensitive matching.
        """
        patterns = [f"(?i){p}" for p in ANTISPAM_WORD_FILTER_PATTERNS]
        too_long = [p for p in patterns if len(p) > MAX_REGEX_LENGTH]
        if too_long:
            raise ValueError(f"AutoMod regex longer than {MAX_REGEX_LENGTH} chars: {too_long}")
        return patterns

    def build_rule_specs(self, alert_channel_id: int) -> List[Dict[str, Any]]:
        """All rules the bot manages, as plain dicts.

        The scam-link rule only *alerts*: the patterns (``discord nitro``,
        ``t.me/``...) are things regular members also say, and the anti-spam
        policy is to act only on brand-new members. AutoMod cannot see join
        age, so it reports the hit and the bot decides; established members
        are never blocked by it. Mention spam and Discord's own spam
        classifier are precise enough to block outright.
        """
        alert = {'type': ACTION_SEND_ALERT, 'channel_id': alert_channel_id}
        block = {'type': ACTION_BLOCK_MESSAGE, 'custom_message': AUTOMOD_BLOCK_MESSAGE}

        specs: List[Dict[str, Any]] = []
        patterns = self.scam_regex_patterns()
        chunks = [patterns[i:i + MAX_REGEX_PER_RULE]
                  for i in range(0, len(patterns), MAX_REGEX_PER_RULE)]
        for index, chunk in enumerate(chunks):
            name = SCAM_RULE_NAME if index == 0 else f"{SCAM_RULE_NAME} ({index + 1})"
            specs.append({
                'name': name,
                'trigger_type': TRIGGER_KEYWORD,
                'trigger': {'regex_patterns': chunk},
                'actions': [dict(alert)],
                'escalate': True,
            })

        specs.append({
            'name': f"{AUTOMOD_RULE_PREFIX} mention spam",
            'trigger_type': TRIGGER_MENTION_SPAM,
            'trigger': {'mention_limit': AUTOMOD_MENTION_LIMIT,
                        'mention_raid_protection': True},
            'actions': [dict(block), dict(alert)],
            'escalate': False,
        })
        specs.append({
            'name': f"{AUTOMOD_RULE_PREFIX} suspected spam",
            'trigger_type': TRIGGER_SPAM,
            'trigger': {},
            'actions': [dict(block), dict(alert)],
            'escalate': False,
        })
        return specs

    @staticmethod
    def is_escalating_rule(rule_name: Optional[str]) -> bool:
        """True for rules whose hits the bot may escalate to a ban."""
        return bool(rule_name) and rule_name.startswith(SCAM_RULE_NAME)

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------
    def plan_reconciliation(
        self,
        existing: Sequence[Tuple[int, str, int]],
        specs: Sequence[Dict[str, Any]],
    ) -> List[Tuple[str, Optional[int], Dict[str, Any], str]]:
        """Work out how to bring a guild's AutoMod rules in line with ``specs``.

        ``existing`` is ``(rule_id, name, trigger_type)`` for every rule in the
        guild. Returns ``(op, rule_id, spec, note)`` steps where ``op`` is
        ``'create'``, ``'update'`` or ``'skip'``. Rules the bot didn't create
        are never touched or deleted.
        """
        by_name = {name: rule_id for rule_id, name, _ in existing}
        steps = []
        for spec in specs:
            rule_id = by_name.get(spec['name'])
            if rule_id is not None:
                steps.append(('update', rule_id, spec, 'updating bot-managed rule'))
                continue

            if spec['trigger_type'] in SINGLETON_TRIGGERS:
                other = next((name for _, name, t in existing if t == spec['trigger_type']), None)
                if other is not None:
                    steps.append(('skip', None, spec,
                                  f"server already has its own rule of this type ('{other}')"))
                    continue

            steps.append(('create', None, spec, 'creating rule'))
        return steps
