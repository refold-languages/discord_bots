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


class CourseConfigSchema(DataSchema):
    """Schema for course configuration data."""
    
    def validate(self, data: Any) -> Tuple[bool, str]:
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        required_fields = ["version", "courses", "last_updated"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate each course
        for course_name, course_data in data.get("courses", {}).items():
            if not isinstance(course_data, dict):
                return False, f"Course {course_name} data must be a dictionary"
            
            required_course_fields = ["role_id", "category_id"]
            for field in required_course_fields:
                if field not in course_data:
                    return False, f"Course {course_name} missing field: {field}"
                
                if not isinstance(course_data[field], int):
                    return False, f"Course {course_name} field {field} must be an integer"
        
        return True, ""
    
    def get_default(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "courses": {},
            "last_updated": datetime.now().isoformat(),
            "metadata": {
                "description": "Course configuration for Refold Course Server",
                "allowed_servers": [1093991079197560912, 778331995297808438],
                "total_courses": 0
            }
        }
    
    def migrate_from_legacy(self, legacy_data: Any) -> Dict[str, Any]:
        # No legacy migration needed for new feature
        return self.get_default()
    
class HomeworkAssignmentsSchema(DataSchema):
    """Schema for homework assignments data."""
    
    def validate(self, data: Any) -> Tuple[bool, str]:
        """Validate homework assignments data."""
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        required_fields = ["version", "assignments", "last_updated"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data["version"], str):
            return False, "Version must be a string"
        
        if not isinstance(data["assignments"], dict):
            return False, "Assignments must be a dictionary"
        
        if not isinstance(data["last_updated"], str):
            return False, "Last_updated must be a string"
        
        # Validate each assignment
        for assignment_id, assignment_data in data["assignments"].items():
            if not isinstance(assignment_data, dict):
                return False, f"Assignment {assignment_id} data must be a dictionary"
            
            required_assignment_fields = [
                "homework_id", "course_name", "title", "content", 
                "scheduled_datetime", "course_day", "status"
            ]
            for field in required_assignment_fields:
                if field not in assignment_data:
                    return False, f"Assignment {assignment_id} missing field: {field}"
        
        return True, ""
    
    def get_default(self) -> Dict[str, Any]:
        """Get default homework assignments structure."""
        return {
            "version": "1.0",
            "assignments": {},
            "last_updated": datetime.now().isoformat(),
            "metadata": {
                "description": "Homework assignment scheduling data",
                "total_assignments": 0
            }
        }
    
    def migrate_from_legacy(self, legacy_data: Any) -> Dict[str, Any]:
        """No legacy migration needed for new feature."""
        return self.get_default()


class ApiKeysSchema(DataSchema):
    """Schema for encrypted API keys storage."""
    
    def validate(self, data: Any) -> Tuple[bool, str]:
        """Validate API keys data."""
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        required_fields = ["version", "keys", "last_updated"]
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        if not isinstance(data["version"], str):
            return False, "Version must be a string"
        
        if not isinstance(data["keys"], dict):
            return False, "Keys must be a dictionary"
        
        if not isinstance(data["last_updated"], str):
            return False, "Last_updated must be a string"
        
        # Validate each key entry
        for service_name, key_data in data["keys"].items():
            if not isinstance(service_name, str):
                return False, f"Service name must be string: {service_name}"
            
            if not isinstance(key_data, dict):
                return False, f"Key data for {service_name} must be a dictionary"
            
            required_key_fields = ["encrypted_key", "created_at"]
            for field in required_key_fields:
                if field not in key_data:
                    return False, f"Key data for {service_name} missing field: {field}"
        
        return True, ""
    
    def get_default(self) -> Dict[str, Any]:
        """Get default API keys structure."""
        return {
            "version": "1.0",
            "keys": {},
            "last_updated": datetime.now().isoformat(),
            "metadata": {
                "description": "Encrypted API keys for external services",
                "total_keys": 0
            }
        }
    
    def migrate_from_legacy(self, legacy_data: Any) -> Dict[str, Any]:
        """No legacy migration needed for new feature."""
        return self.get_default()