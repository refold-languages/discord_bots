"""
Thread service for Refold Helper Bot.
Handles automated thread scheduling and management business logic with comprehensive logging and error handling.
"""

from datetime import datetime, timedelta
from typing import List, Set, Tuple

import pytz

from .base_service import BaseService
from core import DataManager
from config.constants import (
    ACCOUNTABILITY_CHANNEL_IDS, GRADS_ACCOUNTABILITY_CHANNEL_IDS,
    DAILY_ACCOUNTABILITY_ROLE_ID, UPVOTE_EMOJI, DOWNVOTE_EMOJI
)
from config.settings import settings
from utils import get_logger, performance_monitor, DataError, safe_execute


class ThreadMessageData:
    """Data class for thread message information."""
    
    def __init__(self, content: str, thread_name: str):
        self.content = content
        self.thread_name = thread_name


class ThreadService(BaseService):
    """Service for managing automated threads and scheduling with comprehensive monitoring."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.thread')
        self.data_manager = DataManager()
    
    def initialize(self) -> None:
        """Initialize the thread service by loading channel configurations."""
        super().initialize()
        self.logger.info("thread_service_initializing")
        
        try:
            # DataManager handles its own initialization
            thread_count = len(self.data_manager.get_thread_channels())
            poll_count = len(self.data_manager.get_poll_channels())
            
            self.logger.info("thread_service_initialized",
                           thread_channels_count=thread_count,
                           poll_channels_count=poll_count)
        except Exception as e:
            self.logger.error("thread_service_initialization_failed",
                            error=str(e),
                            error_type=type(e).__name__)
            raise
    
    def calculate_next_daily_occurrence(self, 
                                       hour: int = None, 
                                       minute: int = None, 
                                       timezone: str = None) -> datetime:
        """
        Calculate the next occurrence of a daily event.
        
        Args:
            hour: Hour of day (0-23), defaults to settings value
            minute: Minute of hour (0-59), defaults to settings value
            timezone: Timezone string, defaults to settings value
            
        Returns:
            Datetime of next occurrence
        """
        hour = hour if hour is not None else settings.DAILY_THREAD_HOUR
        minute = minute if minute is not None else settings.DAILY_THREAD_MINUTE
        timezone = timezone or settings.TIMEZONE
        
        self.logger.debug("calculating_next_daily_occurrence",
                         hour=hour,
                         minute=minute,
                         timezone=timezone)
        
        try:
            now = datetime.now(pytz.timezone(timezone))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_time <= now:
                target_time += timedelta(days=1)
            
            self.logger.debug("next_daily_occurrence_calculated",
                            next_occurrence=target_time.isoformat(),
                            seconds_until=int((target_time - now).total_seconds()))
            
            return target_time
            
        except Exception as e:
            self.logger.error("daily_occurrence_calculation_failed",
                            hour=hour,
                            minute=minute,
                            timezone=timezone,
                            error=str(e))
            raise
    
    def calculate_next_weekly_occurrence(self,
                                        hour: int = None,
                                        minute: int = None, 
                                        day_of_week: int = None,
                                        timezone: str = None) -> datetime:
        """
        Calculate the next occurrence of a weekly event.
        
        Args:
            hour: Hour of day (0-23), defaults to settings value
            minute: Minute of hour (0-59), defaults to settings value
            day_of_week: Day of week (0=Monday, 6=Sunday), defaults to settings value
            timezone: Timezone string, defaults to settings value
            
        Returns:
            Datetime of next occurrence
        """
        hour = hour if hour is not None else settings.WEEKLY_THREAD_HOUR
        minute = minute if minute is not None else settings.WEEKLY_THREAD_MINUTE
        day_of_week = day_of_week if day_of_week is not None else settings.WEEKLY_THREAD_DAY
        timezone = timezone or settings.TIMEZONE
        
        self.logger.debug("calculating_next_weekly_occurrence",
                         hour=hour,
                         minute=minute,
                         day_of_week=day_of_week,
                         timezone=timezone)
        
        try:
            now = datetime.now(pytz.timezone(timezone))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            days_ahead = (day_of_week - now.weekday() + 7) % 7
            if days_ahead == 0 and target_time <= now:
                days_ahead = 7
            
            result = target_time + timedelta(days=days_ahead)
            
            self.logger.debug("next_weekly_occurrence_calculated",
                            next_occurrence=result.isoformat(),
                            seconds_until=int((result - now).total_seconds()),
                            days_ahead=days_ahead)
            
            return result
            
        except Exception as e:
            self.logger.error("weekly_occurrence_calculation_failed",
                            hour=hour,
                            minute=minute,
                            day_of_week=day_of_week,
                            timezone=timezone,
                            error=str(e))
            raise
    
    def generate_daily_accountability_message(self, timestamp: int) -> ThreadMessageData:
        """
        Generate daily accountability message and thread name.
        
        Args:
            timestamp: Unix timestamp for the message
            
        Returns:
            ThreadMessageData with message content and thread name
        """
        try:
            content = (
                f"Hello <@&{DAILY_ACCOUNTABILITY_ROLE_ID}>! Today is <t:{timestamp}:D>. "
                "How was your language learning today? What did you do? "
                "Did you struggle with anything? Or did you have any particular wins today? "
                "Post your replies in the thread below!\n\n"
                "If today's been a tough day for your language learning, there's still time! "
                "Go do 5 minutes of an easy activity you enjoy 😁"
            )
            
            # Generate thread name from timestamp
            date_obj = datetime.fromtimestamp(timestamp)
            thread_name = f"Daily Accountability {date_obj.strftime('%Y-%m-%d')}"
            
            self.logger.debug("daily_accountability_message_generated",
                            timestamp=timestamp,
                            thread_name=thread_name,
                            content_length=len(content))
            
            return ThreadMessageData(content, thread_name)
            
        except Exception as e:
            self.logger.error("daily_message_generation_failed",
                            timestamp=timestamp,
                            error=str(e))
            raise
    
    def generate_weekly_graduate_message(self, timestamp: int) -> ThreadMessageData:
        """
        Generate weekly graduate check-in message and thread name.
        
        Args:
            timestamp: Unix timestamp for the message
            
        Returns:
            ThreadMessageData with message content and thread name
        """
        try:
            content = (
                "Greetings, @everyone, it's time for the weekly check-in!\n"
                "1. What are you working on?\n"
                "2. What are you learning?\n"
                "3. What is your most recent win?\n\n"
                "Share your accolades and accomplishments with the rest of the academy below!"
            )
            
            # Generate thread name from timestamp
            date_obj = datetime.fromtimestamp(timestamp)
            thread_name = f"Weekly Check-in - {date_obj.strftime('%Y-%m-%d')}"
            
            self.logger.debug("weekly_graduate_message_generated",
                            timestamp=timestamp,
                            thread_name=thread_name,
                            content_length=len(content))
            
            return ThreadMessageData(content, thread_name)
            
        except Exception as e:
            self.logger.error("weekly_message_generation_failed",
                            timestamp=timestamp,
                            error=str(e))
            raise
    
    def get_accountability_channels(self) -> List[int]:
        """Get list of daily accountability channel IDs."""
        channels = list(ACCOUNTABILITY_CHANNEL_IDS)
        self.logger.debug("accountability_channels_requested", 
                         channel_count=len(channels),
                         channel_ids=channels)
        return channels
    
    def get_graduate_channels(self) -> List[int]:
        """Get list of graduate accountability channel IDs."""
        channels = list(GRADS_ACCOUNTABILITY_CHANNEL_IDS)
        self.logger.debug("graduate_channels_requested",
                         channel_count=len(channels),
                         channel_ids=channels)
        return channels
    
    def should_create_thread(self, channel_id: int) -> bool:
        """
        Check if a channel should have auto-thread creation.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if threads should be auto-created
        """
        self._ensure_initialized()
        
        try:
            thread_channels = self.data_manager.get_thread_channels()
            should_create = channel_id in thread_channels
            
            self.logger.debug("thread_creation_check",
                            channel_id=channel_id,
                            should_create=should_create,
                            total_thread_channels=len(thread_channels))
            
            return should_create
            
        except Exception as e:
            self.logger.error("thread_creation_check_failed",
                            channel_id=channel_id,
                            error=str(e))
            return False
    
    def should_add_poll_reactions(self, channel_id: int) -> bool:
        """
        Check if a channel should have auto-poll reactions.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if poll reactions should be added
        """
        self._ensure_initialized()
        
        try:
            poll_channels = self.data_manager.get_poll_channels()
            should_add = channel_id in poll_channels
            
            self.logger.debug("poll_reaction_check",
                            channel_id=channel_id,
                            should_add=should_add,
                            total_poll_channels=len(poll_channels))
            
            return should_add
            
        except Exception as e:
            self.logger.error("poll_reaction_check_failed",
                            channel_id=channel_id,
                            error=str(e))
            return False
    
    def generate_thread_name_from_message(self, message_content: str) -> str:
        """
        Generate a thread name from message content.
        
        Args:
            message_content: Content of the message
            
        Returns:
            Generated thread name
        """
        try:
            if not message_content:
                self.logger.debug("empty_message_content_for_thread_name")
                return "New Thread"
            
            # Take first 5 words and add ellipsis
            words = str(message_content).split()[:5]
            title = " ".join(words)
            
            # Sanitize and truncate
            title = self.sanitize_string(title, max_length=90)
            
            if len(words) >= 5 or len(message_content) > 50:
                title += "..."
            
            result = title or "New Thread"
            
            self.logger.debug("thread_name_generated",
                            original_content_length=len(message_content),
                            generated_name=result,
                            word_count=len(words))
            
            return result
            
        except Exception as e:
            self.logger.error("thread_name_generation_failed",
                            message_content_length=len(message_content) if message_content else 0,
                            error=str(e))
            return "New Thread"
    
    def get_poll_reactions(self) -> Tuple[str, str]:
        """
        Get the upvote and downvote emoji for polls.
        
        Returns:
            Tuple of (upvote_emoji, downvote_emoji)
        """
        reactions = (UPVOTE_EMOJI, DOWNVOTE_EMOJI)
        self.logger.debug("poll_reactions_requested", 
                         upvote=reactions[0],
                         downvote=reactions[1])
        return reactions
    
    @safe_execute("add_thread_channel")
    async def add_thread_channel(self, channel_id: int) -> bool:
        """
        Add a channel to auto-thread list.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if added successfully, False if already exists
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("add_thread_channel", channel_id=channel_id):
            self.logger.info("thread_channel_add_requested", channel_id=channel_id)
            
            result = self.data_manager.add_thread_channel(channel_id)
            
            self.logger.info("thread_channel_add_completed",
                           channel_id=channel_id,
                           success=result,
                           was_new=result)
            
            return result
    
    @safe_execute("remove_thread_channel")
    async def remove_thread_channel(self, channel_id: int) -> bool:
        """
        Remove a channel from auto-thread list.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if removed successfully, False if not found
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("remove_thread_channel", channel_id=channel_id):
            self.logger.info("thread_channel_remove_requested", channel_id=channel_id)
            
            result = self.data_manager.remove_thread_channel(channel_id)
            
            self.logger.info("thread_channel_remove_completed",
                           channel_id=channel_id,
                           success=result,
                           was_found=result)
            
            return result
    
    @safe_execute("add_poll_channel")
    async def add_poll_channel(self, channel_id: int) -> bool:
        """
        Add a channel to auto-poll list.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if added successfully, False if already exists
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("add_poll_channel", channel_id=channel_id):
            self.logger.info("poll_channel_add_requested", channel_id=channel_id)
            
            result = self.data_manager.add_poll_channel(channel_id)
            
            self.logger.info("poll_channel_add_completed",
                           channel_id=channel_id,
                           success=result,
                           was_new=result)
            
            return result
    
    @safe_execute("remove_poll_channel")
    async def remove_poll_channel(self, channel_id: int) -> bool:
        """
        Remove a channel from auto-poll list.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if removed successfully, False if not found
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("remove_poll_channel", channel_id=channel_id):
            self.logger.info("poll_channel_remove_requested", channel_id=channel_id)
            
            result = self.data_manager.remove_poll_channel(channel_id)
            
            self.logger.info("poll_channel_remove_completed",
                           channel_id=channel_id,
                           success=result,
                           was_found=result)
            
            return result
    
    @safe_execute("clear_thread_channels")
    async def clear_all_thread_channels(self) -> bool:
        """
        Clear all auto-thread channels.
        
        Returns:
            True if cleared successfully
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("clear_thread_channels"):
            old_count = len(self.data_manager.get_thread_channels())
            self.logger.info("thread_channels_clear_requested", current_count=old_count)
            
            result = self.data_manager.clear_thread_channels()
            
            self.logger.info("thread_channels_clear_completed",
                           success=result,
                           channels_cleared=old_count)
            
            return result
    
    def get_thread_channels(self) -> Set[int]:
        """Get copy of current thread channels set."""
        self._ensure_initialized()
        
        channels = self.data_manager.get_thread_channels()
        self.logger.debug("thread_channels_retrieved", 
                         channel_count=len(channels))
        return channels
    
    def get_poll_channels(self) -> Set[int]:
        """Get copy of current poll channels set."""
        self._ensure_initialized()
        
        channels = self.data_manager.get_poll_channels()
        self.logger.debug("poll_channels_retrieved",
                         channel_count=len(channels))
        return channels
    
    def get_channel_configuration_summary(self) -> dict:
        """
        Get summary of current channel configurations.
        
        Returns:
            Dictionary with channel configuration info
        """
        self._ensure_initialized()
        
        try:
            thread_channels = self.get_thread_channels()
            poll_channels = self.get_poll_channels()
            
            summary = {
                "thread_channels": {
                    "count": len(thread_channels),
                    "channels": list(thread_channels)
                },
                "poll_channels": {
                    "count": len(poll_channels), 
                    "channels": list(poll_channels)
                },
                "accountability_channels": {
                    "daily": list(ACCOUNTABILITY_CHANNEL_IDS),
                    "weekly": list(GRADS_ACCOUNTABILITY_CHANNEL_IDS)
                }
            }
            
            self.logger.info("channel_configuration_summary_generated",
                           thread_count=summary["thread_channels"]["count"],
                           poll_count=summary["poll_channels"]["count"],
                           daily_accountability_count=len(summary["accountability_channels"]["daily"]),
                           weekly_accountability_count=len(summary["accountability_channels"]["weekly"]))
            
            return summary
            
        except Exception as e:
            self.logger.error("channel_configuration_summary_failed",
                            error=str(e),
                            error_type=type(e).__name__)
            raise