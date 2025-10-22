"""
Configuration and constants for Refold Coaching Bot.
"""

import os
import argparse
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration management for the coaching bot."""
    
    def __init__(self):
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Refold Coaching Bot')
        parser.add_argument('bot_token', type=str, nargs='?', 
                          help='Discord bot token (can also use BOT_TOKEN env var)')
        args, _ = parser.parse_known_args()
        
        # Bot authentication
        self.BOT_TOKEN = args.bot_token or os.getenv('BOT_TOKEN') or os.getenv('DISCORD_BOT_TOKEN')
        if not self.BOT_TOKEN:
            raise ValueError("Bot token must be provided via command line, BOT_TOKEN, or DISCORD_BOT_TOKEN environment variable")
        
        # OpenAI API key
        self.OPENAI_API_KEY = self._get_openai_key()
        
        # Discord configuration
        self.INTENSIVE_ROLE_ID = int(os.getenv('INTENSIVE_ROLE_ID', '0'))
        self.COACH_ROLE_ID = int(os.getenv('COACH_ROLE_ID', '0'))
        self.COACH_CHANNEL_ID = int(os.getenv('COACH_CHANNEL_ID', '0'))
        self.BOT_CHAT_CHANNEL_ID = int(os.getenv('BOT_CHAT_CHANNEL_ID', '0'))
        self.INTENSIVE_JOIN_CHANNEL_ID = int(os.getenv('INTENSIVE_JOIN_CHANNEL_ID', '0'))
        self.INTENSIVE_CHAT_ROOM_ID = int(os.getenv('INTENSIVE_CHAT_ROOM_ID', '0'))
        self.ACTIVITY_FEED_CHANNEL_ID = 1280352810118025278
        
        # Bot settings
        self.COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '&')
        
        # Scheduling (all times in Pacific Time)
        self.DAILY_SUMMARY_HOUR = int(os.getenv('DAILY_SUMMARY_HOUR', '20'))  # 8 PM Pacific
        self.REACHOUT_THRESHOLD_DAYS = int(os.getenv('REACHOUT_THRESHOLD_DAYS', '3'))
        self.REACHOUT_THRESHOLD_MESSAGES = int(os.getenv('REACHOUT_THRESHOLD_MESSAGES', '5'))
        self.TIMEZONE = os.getenv('TIMEZONE', 'America/Los_Angeles')  # Pacific Time
        
        # Data storage
        self.DATA_DIR = os.getenv('DATA_DIR', './data')
        self.PROMPTS_DIR = os.getenv('PROMPTS_DIR', './prompts')
        
        # Validate required settings
        self._validate()
    
    def _get_openai_key(self) -> str:
        """Get OpenAI API key from file or environment."""
        # Try to read from openaiapi.txt file first (like grammar bot)
        try:
            with open('openaiapi.txt', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            pass
        
        # Fall back to environment variable
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            raise ValueError("OpenAI API key must be provided in openaiapi.txt file or OPENAI_API_KEY environment variable")
        return key
    
    def _validate(self):
        """Validate required configuration."""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        
        if self.INTENSIVE_ROLE_ID == 0:
            print("Warning: INTENSIVE_ROLE_ID not set - users won't get roles")
        
        if self.COACH_CHANNEL_ID == 0:
            print("Warning: COACH_CHANNEL_ID not set - coach features disabled")
        
        if self.BOT_CHAT_CHANNEL_ID == 0:
            print("Warning: BOT_CHAT_CHANNEL_ID not set - bot chat features disabled")
        
        if self.INTENSIVE_JOIN_CHANNEL_ID == 0:
            print("Warning: INTENSIVE_JOIN_CHANNEL_ID not set - onboarding features disabled")
        if self.INTENSIVE_CHAT_ROOM_ID == 0:
            print("Warning: INTENSIVE_CHAT_ROOM_ID not set - completion message will have generic channel references")


# Global config instance
config = Config()
