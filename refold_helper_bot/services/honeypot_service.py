"""
Honeypot service for Refold Helper Bot.
Business logic for the spam honeypot: deciding whether a message should
trigger a ban and keeping a durable record of every ban that happens.

This service is intentionally free of Discord API calls. The cog computes
plain values from Discord objects and passes them in here.
"""

import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

from .base_service import BaseService
from config.constants import (
    HONEYPOT_CHANNEL_NAME,
    HONEYPOT_BAN_DELETE_MESSAGE_SECONDS,
    HONEYPOT_RECORD_FILE,
)
from config.settings import settings
from utils import get_logger


class HoneypotService(BaseService):
    """Decides honeypot bans and persists a record of them."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.honeypot')
        self._record_path = os.path.join(settings.DATA_DIR, HONEYPOT_RECORD_FILE)

    def initialize(self) -> None:
        """Initialize the service and ensure the record file's directory exists."""
        super().initialize()
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        existing = len(self.get_ban_records())
        self.logger.info("honeypot_service_initialized",
                         channel_name=HONEYPOT_CHANNEL_NAME,
                         record_path=self._record_path,
                         existing_records=existing)

    def is_honeypot_channel(self, channel_name: str) -> bool:
        """Return True if a channel's name marks it as the spam honeypot."""
        if not channel_name:
            return False
        return channel_name.strip().lower() == HONEYPOT_CHANNEL_NAME.lower()

    def is_exempt(self, *, is_bot: bool, is_guild_owner: bool,
                  has_staff_powers: bool) -> bool:
        """
        Decide whether a poster is protected from the honeypot.

        Bots (including this one), the guild owner, and anyone with
        moderator/admin powers are exempt so staff can post the warning
        message that explains what the channel is.
        """
        return is_bot or is_guild_owner or has_staff_powers

    def get_ban_delete_seconds(self) -> int:
        """Seconds of message history to purge when banning a spammer."""
        return HONEYPOT_BAN_DELETE_MESSAGE_SECONDS

    def build_ban_record(self, *, user_id: int, user_name: str,
                         guild_id: int, guild_name: str,
                         channel_id: int, channel_name: str,
                         message_content: str) -> Dict[str, Any]:
        """Build a structured record describing why a user was banned."""
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'user_id': user_id,
            'user_name': user_name,
            'guild_id': guild_id,
            'guild_name': guild_name,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'reason': 'Posted in the spam honeypot channel.',
            'message_content': self.sanitize_string(message_content or '', max_length=1000),
            'messages_purged_seconds': self.get_ban_delete_seconds(),
        }

    def get_ban_records(self) -> List[Dict[str, Any]]:
        """Load all honeypot ban records (newest last). Empty list on any issue."""
        try:
            if not os.path.exists(self._record_path):
                return []
            with open(self._record_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as e:
            self.logger.error("honeypot_record_read_failed",
                              error=str(e), error_type=type(e).__name__)
            return []

    def record_ban(self, record: Dict[str, Any]) -> bool:
        """
        Append a ban record to the durable JSON file.

        Uses an atomic write (temp file + replace) so a crash mid-write
        can't corrupt the existing history.
        """
        try:
            records = self.get_ban_records()
            records.append(record)

            os.makedirs(settings.DATA_DIR, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=settings.DATA_DIR,
                                            prefix='.honeypot_', suffix='.tmp')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(records, f, indent=2, default=str)
                os.replace(tmp_path, self._record_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise

            self.logger.info("honeypot_ban_recorded",
                             user_id=record.get('user_id'),
                             guild_id=record.get('guild_id'),
                             total_records=len(records))
            return True
        except OSError as e:
            self.logger.error("honeypot_record_write_failed",
                              error=str(e), error_type=type(e).__name__)
            return False
