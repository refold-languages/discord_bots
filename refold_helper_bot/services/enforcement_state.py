"""
Shared runtime enforcement state for all spam/ban features.

A single in-memory + persisted source of truth consulted by BOTH the honeypot
and the anti-spam cogs. This is what lets one command:

  * emergency-disable every automatic ban/timeout at once (kill switch), and
  * flip the whole moderation stack into a non-destructive *test mode*, where
    the bot reacts to messages that WOULD be actioned instead of acting.

Exposed as a module-level singleton (``enforcement_state``) so every cog that
imports it shares the same object, exactly like ``config.settings.settings``.
State is also persisted so it survives a restart.
"""

import json
import os
import tempfile
from typing import Any, Dict

from config.settings import settings
from utils import get_logger

ENFORCEMENT_STATE_FILE = 'enforcement_state.json'


class EnforcementState:
    """Global on/off + test-mode flags for the moderation stack."""

    def __init__(self):
        self.logger = get_logger('services.enforcement_state')
        self._path = os.path.join(settings.DATA_DIR, ENFORCEMENT_STATE_FILE)
        self._enabled = True
        self._test_mode = False
        self._loaded = False

    def initialize(self) -> None:
        """Load persisted state. Idempotent; safe for multiple cogs to call."""
        if self._loaded:
            return
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        data = self._read()
        self._enabled = bool(data.get('enabled', True))
        self._test_mode = bool(data.get('test_mode', False))
        self._loaded = True
        self.logger.info("enforcement_state_initialized",
                         enabled=self._enabled, test_mode=self._test_mode)

    # --- reads ---------------------------------------------------------
    def is_enabled(self) -> bool:
        """False means the kill switch is engaged: take NO automatic action."""
        return self._enabled

    def is_test_mode(self) -> bool:
        """True means detect-and-react only; never ban/timeout/delete."""
        return self._test_mode

    def snapshot(self) -> Dict[str, bool]:
        return {'enabled': self._enabled, 'test_mode': self._test_mode}

    # --- writes --------------------------------------------------------
    def set_enabled(self, value: bool) -> bool:
        self._enabled = bool(value)
        return self._save()

    def set_test_mode(self, value: bool) -> bool:
        self._test_mode = bool(value)
        return self._save()

    # --- persistence ---------------------------------------------------
    def _read(self) -> Dict[str, Any]:
        try:
            if not os.path.exists(self._path):
                return {}
            with open(self._path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as e:
            self.logger.error("enforcement_state_read_failed",
                              error=str(e), error_type=type(e).__name__)
            return {}

    def _save(self) -> bool:
        try:
            os.makedirs(settings.DATA_DIR, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=settings.DATA_DIR,
                                            prefix='.enfstate_', suffix='.tmp')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(self.snapshot(), f, indent=2)
                os.replace(tmp_path, self._path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                raise
            self.logger.info("enforcement_state_saved", **self.snapshot())
            return True
        except OSError as e:
            self.logger.error("enforcement_state_write_failed",
                              error=str(e), error_type=type(e).__name__)
            return False


# Module-level singleton shared across all cogs.
enforcement_state = EnforcementState()
