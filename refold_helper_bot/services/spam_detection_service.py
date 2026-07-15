"""
Spam detection service for Refold Helper Bot.

Heuristic, behaviour-based spam detection that runs alongside the honeypot.
The honeypot catches bots that post in the trap channel; this watches how a
user behaves across the whole server and decides on an escalating action.

Like the other services this is intentionally free of Discord API calls: the
cog turns Discord objects into plain values, passes them to :meth:`evaluate`,
and acts on the returned decision. That keeps the detection logic unit-testable
and side-effect free.

Detection state (the sliding windows of recent activity) lives in memory only,
since it describes the last few seconds of behaviour. Every action the engine
recommends is, however, persisted to a durable JSON record so staff can audit
and reverse false positives, and per-guild on/off overrides are persisted too.
"""

import json
import os
import re
import tempfile
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Tuple

from .base_service import BaseService
from config.constants import (
    ANTISPAM_ENABLED,
    ANTISPAM_GUILD_IDS,
    ANTISPAM_IMAGE_MAX,
    ANTISPAM_IMAGE_WINDOW,
    ANTISPAM_LONE_IMAGE_MIN,
    ANTISPAM_LONE_IMAGE_WINDOW,
    ANTISPAM_CROSS_CHANNEL_MAX,
    ANTISPAM_CROSS_CHANNEL_WINDOW,
    ANTISPAM_REPEAT_MAX,
    ANTISPAM_REPEAT_WINDOW,
    ANTISPAM_NEW_USER_MINUTES,
    ANTISPAM_WORD_FILTER_PATTERNS,
    ANTISPAM_NEW_ACCOUNT_DAYS,
    ANTISPAM_CAPTION_MIN_LEN,
    ANTISPAM_ESTABLISHED_MINUTES,
    ANTISPAM_BAN_DELETE_MESSAGE_SECONDS,
    ANTISPAM_TIMEOUT_SECONDS,
    ANTISPAM_RECORD_FILE,
    ANTISPAM_CONFIG_FILE,
)
from config.settings import settings
from utils import get_logger


# Action tiers returned by the engine.
ACTION_NONE = 'none'
ACTION_TIMEOUT = 'timeout'
ACTION_BAN = 'ban'

# Drop tracked content shorter than this from the repeat/cross-channel
# detectors. Pure-image posts and one-word messages ("hi", "lol") would
# otherwise collide constantly; image spam is caught by the image detector.
_MIN_TRACKED_CONTENT_LEN = 4

# How many evaluate() calls between opportunistic memory sweeps.
_SWEEP_EVERY = 500


class _Event:
    """A single recent message by a user, kept in the sliding window."""

    __slots__ = ('ts', 'image_count', 'content', 'channel_id', 'message_id')

    def __init__(self, ts: float, image_count: int, content: str,
                 channel_id: int, message_id: int):
        self.ts = ts
        self.image_count = image_count
        self.content = content
        self.channel_id = channel_id
        self.message_id = message_id


class SpamDetectionService(BaseService):
    """Behavioural spam detection + a tiered action engine."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.spam_detection')
        self._record_path = os.path.join(settings.DATA_DIR, ANTISPAM_RECORD_FILE)
        self._config_path = os.path.join(settings.DATA_DIR, ANTISPAM_CONFIG_FILE)

        # (guild_id, user_id) -> deque[_Event], newest last.
        self._events: Dict[Tuple[int, int], Deque[_Event]] = defaultdict(deque)
        # (guild_id, user_id) of members who have posted real text at any point
        # this process has been running. Having a genuine presence like this
        # means we will never auto-ban them on image heuristics alone. This is a
        # deliberately forgiving "has real messages in the server" signal; it
        # lives in memory only, which is fine — it can only ever spare a user.
        self._legit_users: set = set()
        # Per-guild runtime enable/disable overrides {guild_id: bool}.
        self._guild_overrides: Dict[int, bool] = {}
        self._eval_count = 0

        # Widest window we ever need to look back over; anything older is junk.
        self._max_window = max(
            ANTISPAM_IMAGE_WINDOW,
            ANTISPAM_CROSS_CHANNEL_WINDOW,
            ANTISPAM_REPEAT_WINDOW,
            ANTISPAM_LONE_IMAGE_WINDOW,
        )

        self._patterns = [
            re.compile(p, re.IGNORECASE) for p in ANTISPAM_WORD_FILTER_PATTERNS
        ]

    def initialize(self) -> None:
        """Initialize the service: ensure data dir exists and load overrides."""
        super().initialize()
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        self._guild_overrides = self._load_config()
        existing = len(self.get_action_records())
        self.logger.info("spam_detection_service_initialized",
                         record_path=self._record_path,
                         guild_overrides=self._guild_overrides,
                         existing_records=existing)

    # ------------------------------------------------------------------
    # Enable / scope checks
    # ------------------------------------------------------------------
    def is_enabled_for_guild(self, guild_id: int) -> bool:
        """True if anti-spam should run in this guild (scope + overrides).

        An explicit per-guild override (set via ``!antispam on|off``) is
        authoritative in BOTH directions: it can force-enable a server that
        isn't in the default network (e.g. a test server) or disable one that
        is. With no override, membership in ``ANTISPAM_GUILD_IDS`` decides.
        """
        if not ANTISPAM_ENABLED:
            return False
        if guild_id in self._guild_overrides:
            return self._guild_overrides[guild_id]
        return guild_id in ANTISPAM_GUILD_IDS

    def set_guild_enabled(self, guild_id: int, enabled: bool) -> bool:
        """Persist a per-guild on/off override. Returns success."""
        self._guild_overrides[guild_id] = enabled
        return self._save_config()

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------
    @staticmethod
    def normalize(content: str) -> str:
        """Normalize message text so trivial variations still match."""
        if not content:
            return ''
        # Lowercase and collapse all runs of whitespace to single spaces.
        return re.sub(r'\s+', ' ', content.strip().lower())

    def matches_word_filter(self, content: str) -> Optional[str]:
        """Return the matching pattern string, or None."""
        if not content:
            return None
        for pat in self._patterns:
            if pat.search(content):
                return pat.pattern
        return None

    def evaluate(self, *, guild_id: int, user_id: int, channel_id: int,
                 message_id: int, timestamp: float, image_count: int,
                 content: str, account_age_days: Optional[float],
                 joined_minutes_ago: Optional[float],
                 has_roles: bool = False,
                 mentions_everyone: bool = False) -> Dict[str, Any]:
        """
        Record a message and decide what action (if any) the user has earned.

        ``image_count`` is the number of images carried by this single message
        (attachments + image embeds). All arguments are plain values computed by
        the cog from the Discord message. ``account_age_days`` /
        ``joined_minutes_ago`` may be ``None`` when unknown (e.g. uncached
        member); detectors degrade gracefully.

        ``has_roles`` (member carries a self-assigned role) and
        ``mentions_everyone`` (the message actually mentioned @everyone/@here,
        not merely typed the text) are cheap trust/scam signals from the cog.

        Guiding principle: only ban on things an innocent member essentially
        never does (scam links, a genuine @everyone ping from a brand-new
        account, identical text spammed across channels by a fresh account).
        Everything image-related, and anything we are not sure about, results at
        most in the soft action — remove the message, brief timeout, and a DM.

        Returns a decision dict::

            {
              'action': 'none' | 'timeout' | 'ban',
              'confidence': 'high' | 'low' | None,
              'reasons': [str, ...],
              'detectors': {...counts...},
              'message_refs': [(channel_id, message_id), ...],
              'image_related': bool,   # soft action was image-driven
            }
        """
        self._eval_count += 1
        if self._eval_count % _SWEEP_EVERY == 0:
            self._sweep(now=timestamp)

        normalized = self.normalize(content)
        key = (guild_id, user_id)
        events = self._events[key]
        events.append(_Event(timestamp, image_count, normalized, channel_id,
                             message_id))
        self._prune(events, now=timestamp)

        reasons: List[str] = []
        detectors: Dict[str, int] = {}

        # A message with a real caption is treated as a legitimate post: images
        # WITH text are exactly what regular members do, so the image detectors
        # below never fire on them. We also remember anyone who posts real text
        # anywhere as an established, "has real messages here" member.
        has_text = len(normalized) >= ANTISPAM_CAPTION_MIN_LEN
        if has_text:
            self._legit_users.add(key)

        # --- Detector: image flood ------------------------------------
        # Several images in a short window with NO caption on any of them.
        # Count individual images so a single multi-attachment message counts
        # for all of them. This is a soft signal only — it never bans.
        images_in_window = sum(
            e.image_count for e in events
            if timestamp - e.ts <= ANTISPAM_IMAGE_WINDOW
        )
        detectors['image_count'] = images_in_window
        image_flood = (not has_text) and images_in_window > ANTISPAM_IMAGE_MAX
        if image_flood:
            reasons.append(
                f"Posted {images_in_window} images with no caption in "
                f"{ANTISPAM_IMAGE_WINDOW}s (limit {ANTISPAM_IMAGE_MAX})."
            )

        # --- Detector: lone image dump --------------------------------
        # A single message with several images, no text, from a user with no
        # other recent activity: the drive-by image scammer. Only worth the
        # (cheap) history scan when this message could actually qualify.
        lone_image_dump = False
        if image_count >= ANTISPAM_LONE_IMAGE_MIN and not normalized:
            other_recent = sum(
                1 for e in events
                if e.message_id != message_id
                and timestamp - e.ts <= ANTISPAM_LONE_IMAGE_WINDOW
            )
            detectors['other_recent'] = other_recent
            lone_image_dump = other_recent == 0
            if lone_image_dump:
                reasons.append(
                    f"Posted {image_count} images with no text and no other "
                    f"messages in the last {ANTISPAM_LONE_IMAGE_WINDOW}s "
                    f"(lone image dump)."
                )

        # --- Repeat / cross-channel (only for non-trivial text) -------
        cross_channel = False
        rapid_repeat = False
        if len(normalized) >= _MIN_TRACKED_CONTENT_LEN:
            same_repeat = [
                e for e in events
                if e.content == normalized
                and timestamp - e.ts <= ANTISPAM_REPEAT_WINDOW
            ]
            same_cross = [
                e for e in events
                if e.content == normalized
                and timestamp - e.ts <= ANTISPAM_CROSS_CHANNEL_WINDOW
            ]
            distinct_channels = len({e.channel_id for e in same_cross})
            detectors['repeat_count'] = len(same_repeat)
            detectors['distinct_channels'] = distinct_channels

            cross_channel = distinct_channels > ANTISPAM_CROSS_CHANNEL_MAX
            rapid_repeat = len(same_repeat) > ANTISPAM_REPEAT_MAX
            if cross_channel:
                reasons.append(
                    f"Posted the same message in {distinct_channels} channels "
                    f"in {ANTISPAM_CROSS_CHANNEL_WINDOW}s "
                    f"(limit {ANTISPAM_CROSS_CHANNEL_MAX})."
                )
            if rapid_repeat:
                reasons.append(
                    f"Repeated the same message {len(same_repeat)} times in "
                    f"{ANTISPAM_REPEAT_WINDOW}s (limit {ANTISPAM_REPEAT_MAX})."
                )

        # --- Detector: word filter for new users ----------------------
        # A scam link (or a genuine @everyone/@here ping) from a member who
        # joined minutes ago. We check the real mention flag, not the literal
        # "@everyone" text, so quoting or discussing it can't trip the filter.
        word_hit = None
        is_new_user = (joined_minutes_ago is not None
                       and joined_minutes_ago <= ANTISPAM_NEW_USER_MINUTES)
        if is_new_user:
            word_hit = self.matches_word_filter(normalized)
            if word_hit:
                reasons.append(
                    f"New member (joined {joined_minutes_ago:.1f}m ago) matched "
                    f"the scam-link filter: /{word_hit}/."
                )
            elif mentions_everyone:
                word_hit = '@everyone/@here mention'
                reasons.append(
                    f"New member (joined {joined_minutes_ago:.1f}m ago) pinged "
                    f"@everyone/@here."
                )

        # --- Tiered decision ------------------------------------------
        # Two trust notions, deliberately different:
        #
        #  * has_presence — used to EXEMPT a user from image-dump enforcement.
        #    Anyone with a role, a history of real text, or some tenure here is
        #    treated as a genuine member, not a drive-by image scammer. This is
        #    forgiving on purpose: the goal is to never punish a regular for
        #    posting screenshots.
        #
        #  * text_trusted — used to decide ban-vs-soft for TEXT spam. It must
        #    NOT include the self-marked legit-text set, or a spam bot's own
        #    messages would vouch for it. Only a role or real server tenure
        #    counts, so a brand-new account cross-posting identical text is
        #    still caught.
        is_new_account = (account_age_days is not None
                          and account_age_days < ANTISPAM_NEW_ACCOUNT_DAYS)
        long_tenure = (joined_minutes_ago is not None
                       and joined_minutes_ago >= ANTISPAM_ESTABLISHED_MINUTES)
        has_presence = has_roles or (key in self._legit_users) or long_tenure
        text_trusted = has_roles or long_tenure
        detectors['has_presence'] = int(has_presence)

        text_spam = cross_channel or rapid_repeat
        image_spam = image_flood or lone_image_dump
        image_related = False

        if word_hit:
            # Scam link / real @everyone ping from a brand-new member: as close
            # to certain as we get. Ban.
            action, confidence = ACTION_BAN, 'high'
        elif text_spam and is_new_account and not text_trusted:
            # Identical text hosed across channels/rapidly by a fresh, unknown
            # account: the classic hacked-account spam bot. Ban.
            action, confidence = ACTION_BAN, 'high'
        elif image_spam and not has_presence:
            # Image dump from someone with no real presence. Not certain enough
            # to ban — could be a new member sharing screenshots. Soft action.
            action, confidence = ACTION_TIMEOUT, 'low'
            image_related = True
        elif text_spam:
            # Repeat/cross-channel that didn't meet the ban bar (established
            # member, or an older account): looks off, but we are not sure.
            # Soft action, no ban.
            action, confidence = ACTION_TIMEOUT, 'low'
        else:
            # Below threshold, or image behaviour from a member with presence.
            action, confidence = ACTION_NONE, None

        # Collect the burst's message references so the cog can delete them.
        # (Ban-tier deletion is handled by Discord's purge-on-ban; this matters
        # for the soft tier, which has no built-in bulk delete.) For text spam
        # it's every recent message with the offending content; for an image
        # burst it's the recent image-bearing messages; otherwise the trigger.
        if text_spam and len(normalized) >= _MIN_TRACKED_CONTENT_LEN:
            message_refs = [(e.channel_id, e.message_id) for e in events
                            if e.content == normalized]
        elif image_related:
            message_refs = [(e.channel_id, e.message_id) for e in events
                            if e.image_count > 0
                            and timestamp - e.ts <= ANTISPAM_IMAGE_WINDOW]
            if not message_refs:
                message_refs = [(channel_id, message_id)]
        else:
            message_refs = [(channel_id, message_id)]

        # On a terminal action, forget the user's window so we don't re-fire
        # on the same evidence for an already-actioned account.
        if action != ACTION_NONE:
            self._events.pop(key, None)

        return {
            'action': action,
            'confidence': confidence,
            'reasons': reasons,
            'detectors': detectors,
            'message_refs': message_refs,
            'image_related': image_related,
        }

    # ------------------------------------------------------------------
    # Action parameters (so the cog doesn't import constants directly)
    # ------------------------------------------------------------------
    def get_ban_delete_seconds(self) -> int:
        return ANTISPAM_BAN_DELETE_MESSAGE_SECONDS

    def get_timeout_seconds(self) -> int:
        return ANTISPAM_TIMEOUT_SECONDS

    # ------------------------------------------------------------------
    # Memory management
    # ------------------------------------------------------------------
    def _prune(self, events: Deque[_Event], *, now: float) -> None:
        """Drop events older than the widest detection window."""
        cutoff = now - self._max_window
        while events and events[0].ts < cutoff:
            events.popleft()

    def _sweep(self, *, now: float) -> None:
        """Periodically drop empty/stale per-user windows to cap memory."""
        cutoff = now - self._max_window
        stale = [
            key for key, ev in self._events.items()
            if not ev or ev[-1].ts < cutoff
        ]
        for key in stale:
            self._events.pop(key, None)
        if stale:
            self.logger.debug("spam_detection_swept", removed=len(stale),
                              tracked=len(self._events))

    # ------------------------------------------------------------------
    # Durable records
    # ------------------------------------------------------------------
    def build_action_record(self, *, action: str, confidence: Optional[str],
                            reasons: List[str], user_id: int, user_name: str,
                            guild_id: int, guild_name: str, channel_id: int,
                            channel_name: str, message_content: str,
                            image_urls: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build a structured record describing an enforcement action.

        ``image_urls`` are the direct links to any images on the triggering
        message, stored so moderators reviewing the log can open them and judge
        for themselves whether this was a scammer or a regular member.
        """
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'action': action,
            'confidence': confidence,
            'reasons': reasons,
            'user_id': user_id,
            'user_name': user_name,
            'guild_id': guild_id,
            'guild_name': guild_name,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'message_content': self.sanitize_string(message_content or '', max_length=1000),
            'image_urls': list(image_urls or []),
        }

    def get_action_records(self) -> List[Dict[str, Any]]:
        """Load all anti-spam action records (newest last). Empty on any issue."""
        return self._read_json_list(self._record_path)

    def record_action(self, record: Dict[str, Any]) -> bool:
        """Append an action record using an atomic write."""
        try:
            records = self.get_action_records()
            records.append(record)
            self._atomic_write_json(self._record_path, records, prefix='.antispam_')
            self.logger.info("antispam_action_recorded",
                             action=record.get('action'),
                             user_id=record.get('user_id'),
                             guild_id=record.get('guild_id'),
                             total_records=len(records))
            return True
        except OSError as e:
            self.logger.error("antispam_record_write_failed",
                              error=str(e), error_type=type(e).__name__)
            return False

    # ------------------------------------------------------------------
    # Per-guild config persistence
    # ------------------------------------------------------------------
    def _load_config(self) -> Dict[int, bool]:
        data = self._read_json_dict(self._config_path)
        overrides: Dict[int, bool] = {}
        for k, v in data.items():
            try:
                overrides[int(k)] = bool(v)
            except (TypeError, ValueError):
                continue
        return overrides

    def _save_config(self) -> bool:
        try:
            # JSON keys must be strings.
            data = {str(k): bool(v) for k, v in self._guild_overrides.items()}
            self._atomic_write_json(self._config_path, data, prefix='.antispamcfg_')
            return True
        except OSError as e:
            self.logger.error("antispam_config_write_failed",
                              error=str(e), error_type=type(e).__name__)
            return False

    # ------------------------------------------------------------------
    # Small JSON helpers (atomic write + safe read)
    # ------------------------------------------------------------------
    def _read_json_list(self, path: str) -> List[Dict[str, Any]]:
        try:
            if not os.path.exists(path):
                return []
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as e:
            self.logger.error("antispam_json_read_failed", path=path,
                              error=str(e), error_type=type(e).__name__)
            return []

    def _read_json_dict(self, path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(path):
                return {}
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as e:
            self.logger.error("antispam_json_read_failed", path=path,
                              error=str(e), error_type=type(e).__name__)
            return {}

    def _atomic_write_json(self, path: str, data: Any, *, prefix: str) -> None:
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=settings.DATA_DIR, prefix=prefix,
                                        suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
