"""
Attendance and activity tracking for Refold Coaching Bot.
Tracks messages, voice activity, and parses activity feed data.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import discord
from data_manager import data_manager
from config import config


class AttendanceTracker:
    """Tracks user attendance and activity."""
    
    def __init__(self):
        # Activity feed parsing pattern
        self.activity_pattern = re.compile(
            r'([🇦-🇿]+)\s+(\w+)\s+did\s+(.+?)\s+for\s+(\d+)\s+(hr|mins?)\.?'
        )
    
    def track_message(self, user_id: int, channel_id: int):
        """Track a user message."""
        # Only track messages in relevant channels (not DMs or bot commands)
        if channel_id == config.BOT_CHAT_CHANNEL_ID:
            data_manager.update_user_attendance(user_id, messages=1)
    
    def track_voice_join(self, user_id: int):
        """Track a user joining a voice channel."""
        data_manager.update_user_attendance(user_id, voice_joins=1)
    
    def track_general_activity(self, user_id: int, channel_id: int):
        """Track general server activity for reachout purposes."""
        # Only track if user is registered for the intensive
        user = data_manager.get_user(user_id)
        if not user:
            return
        
        # Track general server activity (messages in any channel except DMs)
        # This helps determine if users are active in the server
        data_manager.update_user_attendance(user_id, messages=1)
    
    def parse_activity_feed_message(self, message: discord.Message) -> Optional[Dict[str, Any]]:
        """Parse activity feed message and extract user activity data."""
        if message.channel.id != config.ACTIVITY_FEED_CHANNEL_ID:
            return None
        
        content = message.content.strip()
        match = self.activity_pattern.search(content)
        
        if not match:
            return None
        
        flag, username, activity, time_value, time_unit = match.groups()
        
        # Convert time to minutes
        minutes = int(time_value)
        if time_unit.startswith('hr'):
            minutes *= 60
        
        # Find user by app username
        user = self._find_user_by_app_username(username)
        if not user:
            return None
        
        # Create activity entry
        activity_entry = {
            'timestamp': datetime.now().isoformat(),
            'username': username,
            'activity': activity,
            'minutes': minutes,
            'flag': flag
        }
        
        # Save to activity feed
        data_manager.save_activity_feed_entry(activity_entry)
        
        # Update user's activity tracking
        data_manager.update_activity_tracking(
            user['discord_id'], 
            minutes, 
            activity
        )
        
        return activity_entry
    
    async def find_matching_username(self, channel, input_username: str) -> Optional[str]:
        """Search activity feed for matching username (case-insensitive partial match)."""
        try:
            # Load activity feed data from JSON file instead of Discord messages
            activity_entries = data_manager.get_recent_activity_feed(days=2)  # Last 2 days
            
            # Extract unique usernames from activity entries
            found_usernames = []
            for entry in activity_entries:
                username = entry.get('username', '')
                if username and username not in found_usernames:
                    found_usernames.append(username)
            
            # Look for matches (case-insensitive)
            input_lower = input_username.lower()
            
            # First try exact match (case-insensitive)
            for username in found_usernames:
                if username.lower() == input_lower:
                    return username
            
            # Then try partial match
            for username in found_usernames:
                if input_lower in username.lower() or username.lower() in input_lower:
                    return username
            
            return None
            
        except Exception as e:
            print(f"Error searching for username: {e}")
            return None
    
    def _find_user_by_app_username(self, app_username: str) -> Optional[Dict[str, Any]]:
        """Find user by their app username."""
        users = data_manager.get_all_users()
        for discord_id, user in users.items():
            if user.get('app_username', '').lower() == app_username.lower():
                return {
                    'discord_id': int(discord_id),
                    'username': user.get('discord_username', ''),
                    'app_username': user.get('app_username', ''),
                    'goals': user.get('goals', '')
                }
        return None
    
    def get_user_activity_summary(self, discord_id: int) -> Dict[str, Any]:
        """Get comprehensive activity summary for a user."""
        user = data_manager.get_user(discord_id)
        if not user:
            return {}
        
        attendance = user.get('attendance', {})
        activity_tracking = user.get('activity_tracking', {})
        
        # Calculate activity metrics
        total_messages = attendance.get('total_messages', 0)
        voice_joins = attendance.get('voice_joins', 0)
        total_minutes = activity_tracking.get('total_minutes', 0)
        
        # Calculate average messages per day
        messages_per_day = attendance.get('messages_per_day', {})
        if messages_per_day:
            avg_messages_per_day = sum(messages_per_day.values()) / len(messages_per_day)
        else:
            avg_messages_per_day = 0
        
        # Calculate days active
        days_active = len(messages_per_day)
        
        # Get recent activity (last 7 days)
        recent_activities = []
        if activity_tracking.get('activities'):
            cutoff_date = datetime.now() - timedelta(days=7)
            for activity in activity_tracking['activities']:
                activity_date = datetime.fromisoformat(activity['timestamp'].replace('Z', '+00:00'))
                if activity_date.replace(tzinfo=None) >= cutoff_date:
                    recent_activities.append(activity)
        
        return {
            'total_messages': total_messages,
            'avg_messages_per_day': round(avg_messages_per_day, 1),
            'days_active': days_active,
            'voice_joins': voice_joins,
            'total_app_minutes': total_minutes,
            'recent_activities': recent_activities,
            'last_active': attendance.get('last_active'),
            'is_active': self._is_user_active(discord_id)
        }
    
    def _is_user_active(self, discord_id: int) -> bool:
        """Check if user is currently active (messages in last 3 days)."""
        user = data_manager.get_user(discord_id)
        if not user or not user.get('attendance'):
            return False
        
        last_active = user['attendance'].get('last_active')
        if not last_active:
            return False
        
        last_active_date = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
        days_since_active = (datetime.now() - last_active_date.replace(tzinfo=None)).days
        
        return days_since_active <= 3
    
    def get_inactive_users(self, days_threshold: int = 3, messages_threshold: int = 5) -> List[Dict[str, Any]]:
        """Get list of inactive users."""
        return data_manager.get_inactive_users(days_threshold, messages_threshold)
    
    def get_activity_stats(self) -> Dict[str, Any]:
        """Get overall activity statistics."""
        users = data_manager.get_all_users()
        
        total_users = len(users)
        active_users = 0
        total_messages = 0
        total_app_minutes = 0
        
        for user in users.values():
            attendance = user.get('attendance', {})
            activity_tracking = user.get('activity_tracking', {})
            
            total_messages += attendance.get('total_messages', 0)
            total_app_minutes += activity_tracking.get('total_minutes', 0)
            
            if self._is_user_active(user.get('discord_id', 0)):
                active_users += 1
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_messages': total_messages,
            'total_app_minutes': total_app_minutes,
            'activity_rate': round((active_users / total_users * 100) if total_users > 0 else 0, 1)
        }


# Global attendance tracker instance
attendance_tracker = AttendanceTracker()
