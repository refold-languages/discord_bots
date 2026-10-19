"""
Base service class for Refold Helper Bot.
Provides common patterns and utilities for all service classes.
"""

from abc import ABC
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


class BaseService(ABC):
    """
    Base class for all service classes.
    
    Services contain business logic and are independent of Discord API calls.
    They should be testable and reusable across different contexts.
    """
    
    def __init__(self):
        """Initialize the base service."""
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize the service.
        
        Override this method in subclasses to perform any setup needed.
        This is called after the service is created but before it's used.
        """
        self._initialized = True
    
    @property
    def is_initialized(self) -> bool:
        """Check if the service has been initialized."""
        return self._initialized
    
    def _ensure_initialized(self) -> None:
        """Ensure the service is initialized before use."""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} must be initialized before use")
    
    def validate_data(self, data: Dict[str, Any], required_fields: list) -> bool:
        """
        Validate that required fields are present in data.
        
        Args:
            data: Dictionary to validate
            required_fields: List of required field names
            
        Returns:
            True if all required fields are present, False otherwise
        """
        return all(field in data for field in required_fields)
    
    def sanitize_string(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize a string for safe use.
        
        Args:
            text: String to sanitize
            max_length: Maximum length to truncate to
            
        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Remove any problematic characters
        text = text.strip()
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rstrip()
        
        return text

    @staticmethod
    def prune_records(records: List[Dict[str, Any]], *, max_age_days: int,
                      max_records: int, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Drop records older than ``max_age_days`` and keep at most the newest ``max_records``.

        Records are expected oldest-first with an ISO-8601 ``timestamp``. A
        record whose timestamp can't be parsed is kept rather than silently
        destroyed; the count cap still bounds the file.
        """
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=max_age_days)

        kept = []
        for record in records:
            try:
                ts = datetime.fromisoformat(str(record.get('timestamp', '')).replace('Z', '+00:00'))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                kept.append(record)
                continue
            if ts >= cutoff:
                kept.append(record)
        return kept[-max_records:] if max_records > 0 else []
