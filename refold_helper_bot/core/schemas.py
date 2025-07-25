"""
Data schemas for Refold Helper Bot.
Defines structure and validation for JSON data files.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Tuple
from datetime import datetime


class DataSchema(ABC):
    """Base class for data schemas."""
    
    @abstractmethod
    def validate(self, data: Any) -> Tuple[bool, str]:
        """
        Validate data against schema.
        
        Args:
            data: Data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_default(self) -> Any:
        """Get default data structure."""
        pass
    
    @abstractmethod
    def migrate_from_legacy(self, legacy_data: Any) -> Any:
        """Migrate from legacy format to new format."""
        pass


class ThreadChannelsSchema(DataSchema):
    """Schema for thread channels configuration."""
    
    def validate(self, data: Any) -> Tuple[bool, str]:
        """Validate thread channels data."""
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        required_fields = ["version", "channels", "last_updated"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data["version"], str):
            return False, "Version must be a string"
        
        if not isinstance(data["channels"], list):
            return False, "Channels must be a list"
        
        if not isinstance(data["last_updated"], str):
            return False, "Last_updated must be a string"
        
        # Validate each channel ID
        for channel_id in data["channels"]:
            if not isinstance(channel_id, int) or channel_id <= 0:
                return False, f"Invalid channel ID: {channel_id}"
        
        return True, ""
    
    def get_default(self) -> Dict[str, Any]:
        """Get default thread channels structure."""
        return {
            "version": "1.0",
            "channels": [],
            "last_updated": datetime.now().isoformat(),
            "metadata": {
                "description": "Auto-thread channel configuration",
                "total_channels": 0
            }
        }
    
    def migrate_from_legacy(self, legacy_data: Any) -> Dict[str, Any]:
        """Migrate from pickle list format to new JSON format."""
        default = self.get_default()
        
        if isinstance(legacy_data, list):
            # Convert list of channel IDs to new format
            valid_channels = [
                int(channel_id) for channel_id in legacy_data 
                if isinstance(channel_id, (int, str)) and str(channel_id).isdigit()
            ]
            default["channels"] = valid_channels
            default["metadata"]["total_channels"] = len(valid_channels)
        
        return default


class PollChannelsSchema(DataSchema):
    """Schema for poll channels configuration."""
    
    def validate(self, data: Any) -> Tuple[bool, str]:
        """Validate poll channels data."""
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        required_fields = ["version", "channels", "last_updated"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data["version"], str):
            return False, "Version must be a string"
        
        if not isinstance(data["channels"], list):
            return False, "Channels must be a list"
        
        if not isinstance(data["last_updated"], str):
            return False, "Last_updated must be a string"
        
        # Validate each channel ID
        for channel_id in data["channels"]:
            if not isinstance(channel_id, int) or channel_id <= 0:
                return False, f"Invalid channel ID: {channel_id}"
        
        return True, ""
    
    def get_default(self) -> Dict[str, Any]:
        """Get default poll channels structure."""
        return {
            "version": "1.0", 
            "channels": [],
            "last_updated": datetime.now().isoformat(),
            "metadata": {
                "description": "Auto-poll channel configuration",
                "total_channels": 0,
                "upvote_emoji": "<:ReUpvote:993947837836558417>",
                "downvote_emoji": "<:ReDownvote:993947836796383333>"
            }
        }
    
    def migrate_from_legacy(self, legacy_data: Any) -> Dict[str, Any]:
        """Migrate from pickle list format to new JSON format."""
        default = self.get_default()
        
        if isinstance(legacy_data, list):
            # Convert list of channel IDs to new format
            valid_channels = [
                int(channel_id) for channel_id in legacy_data 
                if isinstance(channel_id, (int, str)) and str(channel_id).isdigit()
            ]
            default["channels"] = valid_channels
            default["metadata"]["total_channels"] = len(valid_channels)
        
        return default


class ProjectsSchema(DataSchema):
    """Schema for projects data (already JSON, but add validation)."""
    
    def validate(self, data: Any) -> Tuple[bool, str]:
        """Validate projects data."""
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        # Each project should have [leader, description] format
        for project_name, project_data in data.items():
            if not isinstance(project_name, str):
                return False, f"Project name must be string: {project_name}"
            
            if not isinstance(project_data, list) or len(project_data) != 2:
                return False, f"Project data must be [leader, description]: {project_name}"
            
            leader, description = project_data
            if not isinstance(leader, str) or not isinstance(description, str):
                return False, f"Leader and description must be strings: {project_name}"
        
        return True, ""
    
    def get_default(self) -> Dict[str, Any]:
        """Get default projects structure."""
        return {}
    
    def migrate_from_legacy(self, legacy_data: Any) -> Dict[str, Any]:
        """Projects are already in correct format."""
        if isinstance(legacy_data, dict):
            return legacy_data
        return self.get_default()