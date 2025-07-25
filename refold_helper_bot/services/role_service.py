"""
Role service for Refold Helper Bot.
Handles all role-related business logic without Discord API dependencies.
"""

import csv
from typing import Dict, List, Optional, Set, Tuple

from .base_service import BaseService
from config.constants import (
    ROLE_MAPPING, REACTION_ROLE_CHANNEL_IDS, THREAD_ROLES, 
    DISQUALIFIED_ROLES, SPANISH_BOOK_CLUB, LANGUAGE_ROLES_FILE
)
from config.settings import settings


class RoleService(BaseService):
    """Service for managing role assignments and cross-server synchronization."""
    
    def __init__(self):
        super().__init__()
        self._language_roles: Dict[str, int] = {}
        self._role_mapping = ROLE_MAPPING.copy()
    
    def initialize(self) -> None:
        """Initialize the role service by loading language roles."""
        super().initialize()
        self._load_language_roles()
    
    def _load_language_roles(self) -> None:
        """Load language role mappings from TSV file."""
        try:
            with open(LANGUAGE_ROLES_FILE, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter='\t')
                self._language_roles = {rows[0]: int(rows[1]) for rows in reader}
        except FileNotFoundError:
            print(f"Warning: {LANGUAGE_ROLES_FILE} not found")
            self._language_roles = {}
        except Exception as e:
            print(f"Error loading language roles: {e}")
            self._language_roles = {}
    
    def should_sync_role(self, guild_id: int) -> bool:
        """
        Check if a guild should have role sync enabled.
        
        Args:
            guild_id: Discord guild ID to check
            
        Returns:
            True if role sync should be enabled for this guild
        """
        self._ensure_initialized()
        return (guild_id != settings.MAIN_SERVER_ID and 
                guild_id in self._role_mapping)
    
    def get_role_for_guild(self, guild_id: int) -> Optional[str]:
        """
        Get the role ID that should be assigned for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Role ID string if mapping exists, None otherwise
        """
        self._ensure_initialized()
        return self._role_mapping.get(guild_id)
    
    def is_reaction_role_channel(self, channel_id: int) -> bool:
        """
        Check if a channel has reaction role functionality enabled.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            True if channel supports reaction roles
        """
        return channel_id in REACTION_ROLE_CHANNEL_IDS
    
    def get_role_for_emoji(self, emoji: str) -> Optional[int]:
        """
        Get role ID for a given emoji in reaction role system.
        
        Args:
            emoji: Emoji string to look up
            
        Returns:
            Role ID if mapping exists, None otherwise
        """
        self._ensure_initialized()
        return self._language_roles.get(emoji)
    
    def is_valid_reaction_emoji(self, emoji: str) -> bool:
        """
        Check if an emoji is valid for reaction roles.
        
        Args:
            emoji: Emoji string to validate
            
        Returns:
            True if emoji maps to a role
        """
        self._ensure_initialized()
        return emoji in self._language_roles
    
    def should_assign_graduate_role(self, thread_id: int, user_role_ids: List[int]) -> Optional[int]:
        """
        Determine if a user should get a graduate role for posting in a thread.
        
        Args:
            thread_id: Discord thread ID
            user_role_ids: List of role IDs the user currently has
            
        Returns:
            Graduate role ID to assign, None if no role should be assigned
        """
        # Check if this thread gives graduate roles
        if thread_id not in THREAD_ROLES:
            return None
        
        # Check if user has any disqualifying roles
        user_roles_set = set(user_role_ids)
        disqualified_set = set(DISQUALIFIED_ROLES)
        
        if user_roles_set & disqualified_set:  # Intersection check
            return None
        
        return THREAD_ROLES[thread_id]
    
    def can_toggle_spanish_book_club(self, user_id: int, guild_member_ids: Set[int]) -> bool:
        """
        Check if a user can toggle Spanish Book Club role.
        
        Args:
            user_id: Discord user ID
            guild_member_ids: Set of user IDs who are members of Spanish guild
            
        Returns:
            True if user can toggle the role
        """
        return user_id in guild_member_ids
    
    def get_spanish_book_club_config(self) -> Tuple[int, int]:
        """
        Get Spanish Book Club guild and role IDs.
        
        Returns:
            Tuple of (guild_id, role_id)
        """
        return SPANISH_BOOK_CLUB['guild_id'], SPANISH_BOOK_CLUB['role_id']
    
    def validate_role_assignment(self, role_id: int, user_id: int) -> bool:
        """
        Validate that a role assignment is safe and allowed.
        
        Args:
            role_id: Role ID to assign
            user_id: User ID to assign to
            
        Returns:
            True if assignment is valid
        """
        # Basic validation - could be expanded with more rules
        if role_id <= 0 or user_id <= 0:
            return False
        
        return True
    
    def get_all_managed_role_ids(self) -> Set[int]:
        """
        Get all role IDs that are managed by this service.
        
        Returns:
            Set of all role IDs under management
        """
        self._ensure_initialized()
        
        managed_roles = set()
        
        # Add cross-server sync roles
        managed_roles.update(int(role_id) for role_id in self._role_mapping.values())
        
        # Add reaction roles
        managed_roles.update(self._language_roles.values())
        
        # Add graduate roles
        managed_roles.update(THREAD_ROLES.values())
        
        # Add special roles
        managed_roles.add(SPANISH_BOOK_CLUB['role_id'])
        
        return managed_roles
    
    def get_language_roles_mapping(self) -> Dict[str, int]:
        """
        Get copy of current language roles mapping.
        
        Returns:
            Dictionary mapping emoji strings to role IDs
        """
        self._ensure_initialized()
        return self._language_roles.copy()
    
    def reload_language_roles(self) -> bool:
        """
        Reload language roles from file.
        
        Returns:
            True if reload was successful
        """
        try:
            self._load_language_roles()
            return True
        except Exception as e:
            print(f"Failed to reload language roles: {e}")
            return False