"""
Data management for Refold Coaching Bot.
Handles JSON storage and loading for user profiles and conversation data.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from config import config


class DataManager:
    """Manages JSON data storage for the coaching bot."""
    
    def __init__(self):
        self.data_dir = config.DATA_DIR
        self.users_file = os.path.join(self.data_dir, 'users.json')
        self.conversations_file = os.path.join(self.data_dir, 'conversations.json')
        self.activity_feed_file = os.path.join(self.data_dir, 'activity_feed.json')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize data files if they don't exist
        self._initialize_files()
    
    def _initialize_files(self):
        """Initialize JSON files with empty structures if they don't exist."""
        if not os.path.exists(self.users_file):
            self._save_json(self.users_file, {})
        
        if not os.path.exists(self.conversations_file):
            self._save_json(self.conversations_file, {})
        
        if not os.path.exists(self.activity_feed_file):
            self._save_json(self.activity_feed_file, [])
    
    def _load_json(self, filepath: str) -> Any:
        """Load JSON data from file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading {filepath}: {e}")
            return {} if 'users' in filepath or 'conversations' in filepath else []
    
    def _save_json(self, filepath: str, data: Any):
        """Save JSON data to file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
    
    def get_user(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile by Discord ID."""
        users = self._load_json(self.users_file)
        return users.get(str(discord_id))
    
    def save_user(self, discord_id: int, user_data: Dict[str, Any]):
        """Save or update user profile."""
        users = self._load_json(self.users_file)
        users[str(discord_id)] = user_data
        self._save_json(self.users_file, users)
    
    def get_all_users(self) -> Dict[str, Any]:
        """Get all user profiles."""
        return self._load_json(self.users_file)
    
    def update_user_attendance(self, discord_id: int, messages: int = 0, voice_joins: int = 0):
        """Update user attendance data."""
        user = self.get_user(discord_id)
        if not user:
            return
        
        if 'attendance' not in user:
            user['attendance'] = {
                'total_messages': 0,
                'messages_per_day': {},
                'voice_joins': 0,
                'last_active': None
            }
        
        # Update message count
        if messages > 0:
            user['attendance']['total_messages'] += messages
            today = datetime.now().strftime('%Y-%m-%d')
            if today not in user['attendance']['messages_per_day']:
                user['attendance']['messages_per_day'][today] = 0
            user['attendance']['messages_per_day'][today] += messages
            user['attendance']['last_active'] = datetime.now().isoformat()
        
        # Update voice joins
        if voice_joins > 0:
            user['attendance']['voice_joins'] += voice_joins
        
        self.save_user(discord_id, user)
    
    def add_conversation_summary(self, discord_id: int, location: str, summary: str, 
                                key_topics: List[str], sentiment: str):
        """Add a conversation summary to user profile."""
        user = self.get_user(discord_id)
        if not user:
            return
        
        if 'conversation_summaries' not in user:
            user['conversation_summaries'] = []
        
        conversation = {
            'date': datetime.now().isoformat(),
            'location': location,
            'summary': summary,
            'key_topics': key_topics,
            'sentiment': sentiment
        }
        
        user['conversation_summaries'].append(conversation)
        self.save_user(discord_id, user)
    
    def add_reachout_conversation(self, discord_id: int, trigger: str, summary: str, outcome: str):
        """Add a reachout conversation to user profile."""
        user = self.get_user(discord_id)
        if not user:
            return
        
        if 'reachouts' not in user:
            user['reachouts'] = {
                'last_reachout': None,
                'total_reachouts': 0,
                'conversations': [],
                'username_verification_sent': False
            }
        
        conversation = {
            'timestamp': datetime.now().isoformat(),
            'trigger': trigger,
            'summary': summary,
            'outcome': outcome
        }
        
        user['reachouts']['conversations'].append(conversation)
        user['reachouts']['total_reachouts'] += 1
        user['reachouts']['last_reachout'] = datetime.now().isoformat()
        
        self.save_user(discord_id, user)
    
    def mark_username_verification_sent(self, discord_id: int):
        """Mark that username verification reachout has been sent to user."""
        user = self.get_user(discord_id)
        if not user:
            return
        
        if 'reachouts' not in user:
            user['reachouts'] = {
                'last_reachout': None,
                'total_reachouts': 0,
                'conversations': [],
                'username_verification_sent': False
            }
        
        user['reachouts']['username_verification_sent'] = True
        self.save_user(discord_id, user)
    
    def has_username_verification_been_sent(self, discord_id: int) -> bool:
        """Check if username verification reachout has been sent to user."""
        user = self.get_user(discord_id)
        if not user:
            return False
        
        reachouts = user.get('reachouts', {})
        return reachouts.get('username_verification_sent', False)
    
    def update_activity_tracking(self, discord_id: int, minutes: int, activity: str):
        """Update user's activity tracking from app feed."""
        user = self.get_user(discord_id)
        if not user:
            return
        
        if 'activity_tracking' not in user:
            user['activity_tracking'] = {
                'total_minutes': 0,
                'activities': []
            }
        
        user['activity_tracking']['total_minutes'] += minutes
        user['activity_tracking']['activities'].append({
            'timestamp': datetime.now().isoformat(),
            'activity': activity,
            'minutes': minutes
        })
        
        self.save_user(discord_id, user)
    
    def get_inactive_users(self, days_threshold: int = 3, messages_threshold: int = 5) -> List[Dict[str, Any]]:
        """Get users who haven't been active recently."""
        users = self.get_all_users()
        inactive = []
        
        for discord_id, user in users.items():
            if not user.get('attendance'):
                continue
            
            attendance = user['attendance']
            last_active = attendance.get('last_active')
            
            if not last_active:
                inactive.append(user)
                continue
            
            # Check if user has been inactive
            last_active_date = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
            days_since_active = (datetime.now() - last_active_date.replace(tzinfo=None)).days
            
            if days_since_active >= days_threshold:
                inactive.append(user)
            elif days_since_active >= 1:
                # Check message count for yesterday
                yesterday = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - 
                           timedelta(days=1)).strftime('%Y-%m-%d')
                yesterday_messages = attendance.get('messages_per_day', {}).get(yesterday, 0)
                if yesterday_messages < messages_threshold:
                    inactive.append(user)
        
        return inactive
    
    def save_activity_feed_entry(self, entry: Dict[str, Any]):
        """Save activity feed entry."""
        entries = self._load_json(self.activity_feed_file)
        entries.append(entry)
        self._save_json(self.activity_feed_file, entries)
    
    def get_recent_activity_feed(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get recent activity feed entries."""
        entries = self._load_json(self.activity_feed_file)
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - \
                     timedelta(days=days)
        
        recent_entries = []
        for entry in entries:
            entry_date = datetime.fromisoformat(entry.get('timestamp', '').replace('Z', '+00:00'))
            if entry_date.replace(tzinfo=None) >= cutoff_date:
                recent_entries.append(entry)
        
        return recent_entries
    
    def save_onboarding_conversation(self, user_id: int, thread_id: int, message_content: str, 
                                   message_type: str, validation_result: Dict[str, Any] = None):
        """Save onboarding conversation data."""
        user = self.get_user(user_id)
        if not user:
            return
        
        if 'onboarding' not in user:
            user['onboarding'] = {
                'thread_id': thread_id,
                'initial_goals_raw': '',
                'goals_iterations': [],
                'final_goals_summary': ''
            }
        
        # Save the message
        if message_type == 'initial_goals':
            user['onboarding']['initial_goals_raw'] = message_content
        
        # Save iteration if it's a goals attempt
        if message_type == 'goals_attempt':
            iteration = {
                'attempt': len(user['onboarding']['goals_iterations']) + 1,
                'goals_text': message_content,
                'validation_result': validation_result or {},
                'timestamp': datetime.now().isoformat()
            }
            user['onboarding']['goals_iterations'].append(iteration)
        
        # Save final summary
        if message_type == 'final_summary':
            user['onboarding']['final_goals_summary'] = message_content
        
        self.save_user(user_id, user)
    
    def update_user_onboarding_status(self, user_id: int, status: str):
        """Update the onboarding status for a user."""
        user = self.get_user(user_id)
        if not user:
            return
        
        if 'onboarding' not in user:
            user['onboarding'] = {}
        
        user['onboarding']['status'] = status
        user['onboarding']['last_updated'] = datetime.now().isoformat()
        
        self.save_user(user_id, user)
    
    def remove_user(self, discord_id: int) -> bool:
        """Remove a user from the system completely."""
        try:
            # Load current users
            users = self.get_all_users()
            
            # Check if user exists
            if str(discord_id) not in users:
                return False
            
            # Remove user from dictionary
            del users[str(discord_id)]
            
            # Save updated users back to file
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error removing user {discord_id}: {e}")
            return False
    
    def get_user_rankings(self, discord_id: int) -> Dict[str, Any]:
        """Get user rankings compared to all other users."""
        try:
            users = self.get_all_users()
            if not users:
                return {
                    'total_minutes_rank': 'N/A',
                    'conversations_rank': 'N/A',
                    'reachouts_rank': 'N/A',
                    'total_users': 0
                }
            
            # Get current user data
            current_user = users.get(str(discord_id))
            if not current_user:
                return {
                    'total_minutes_rank': 'N/A',
                    'conversations_rank': 'N/A',
                    'reachouts_rank': 'N/A',
                    'total_users': len(users)
                }
            
            # Collect all user stats for ranking
            user_stats = []
            for user_id, user_data in users.items():
                activity_tracking = user_data.get('activity_tracking', {})
                reachouts = user_data.get('reachouts', {})
                conversation_summaries = user_data.get('conversation_summaries', [])
                
                user_stats.append({
                    'user_id': user_id,
                    'total_minutes': activity_tracking.get('total_minutes', 0),
                    'conversations': len(conversation_summaries),
                    'reachouts': reachouts.get('total_reachouts', 0)
                })
            
            # Sort by each metric
            user_stats.sort(key=lambda x: x['total_minutes'], reverse=True)
            total_minutes_rank = next((i + 1 for i, user in enumerate(user_stats) if user['user_id'] == str(discord_id)), len(user_stats))
            
            user_stats.sort(key=lambda x: x['conversations'], reverse=True)
            conversations_rank = next((i + 1 for i, user in enumerate(user_stats) if user['user_id'] == str(discord_id)), len(user_stats))
            
            user_stats.sort(key=lambda x: x['reachouts'], reverse=True)
            reachouts_rank = next((i + 1 for i, user in enumerate(user_stats) if user['user_id'] == str(discord_id)), len(user_stats))
            
            return {
                'total_minutes_rank': total_minutes_rank,
                'conversations_rank': conversations_rank,
                'reachouts_rank': reachouts_rank,
                'total_users': len(users)
            }
            
        except Exception as e:
            print(f"Error calculating user rankings: {e}")
            return {
                'total_minutes_rank': 'N/A',
                'conversations_rank': 'N/A',
                'reachouts_rank': 'N/A',
                'total_users': 0
            }


# Global data manager instance
data_manager = DataManager()
