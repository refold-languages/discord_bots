"""
Data manager for Refold Helper Bot.
Handles all data storage operations with validation and backup capabilities.
"""

import json
import pickle
import shutil
import base64
from datetime import datetime
from os import path, makedirs
from typing import Any, Dict, List, Optional, Set, Tuple
from cryptography.fernet import Fernet

from .schemas import DataSchema, ThreadChannelsSchema, PollChannelsSchema, ProjectsSchema, CourseConfigSchema, HomeworkAssignmentsSchema, ApiKeysSchema

class DataManager:
    """Unified data manager with schema validation and backup capabilities."""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.backup_dir = path.join(data_dir, "backups")
        
        # Ensure directories exist
        makedirs(self.data_dir, exist_ok=True)
        makedirs(self.backup_dir, exist_ok=True)
        
        # Initialize encryption key
        self._encryption_key = self._get_or_create_encryption_key()
        
        # Register schemas
        self.schemas = {
            "thread_channels": ThreadChannelsSchema(),
            "poll_channels": PollChannelsSchema(), 
            "projects": ProjectsSchema(),
            "course_config": CourseConfigSchema(),
            "homework_assignments": HomeworkAssignmentsSchema(),
            "api_keys": ApiKeysSchema(),
        }
    
    def _get_or_create_encryption_key(self) -> Fernet:
        """Get or create encryption key for API keys."""
        key_file = path.join(self.data_dir, ".encryption_key")
        
        if path.exists(key_file):
            with open(key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Make the key file read-only
            import os
            os.chmod(key_file, 0o600)
        
        return Fernet(key)
    
    def _get_json_path(self, data_type: str) -> str:
        """Get JSON file path for data type."""
        return path.join(self.data_dir, f"{data_type}.json")
    
    def _get_legacy_path(self, data_type: str) -> str:
        """Get legacy pickle file path for data type."""
        legacy_names = {
            "thread_channels": "thread_channels.dat",
            "poll_channels": "poll_channels.dat",
        }
        legacy_name = legacy_names.get(data_type, f"{data_type}.dat")
        return legacy_name  # These are in project root, not data dir
    
    def _create_backup(self, file_path: str) -> bool:
        """Create backup of a file."""
        if not path.exists(file_path):
            return True
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = path.basename(file_path)
            backup_path = path.join(self.backup_dir, f"{filename}.backup_{timestamp}")
            shutil.copy2(file_path, backup_path)
            return True
        except Exception as e:
            print(f"Failed to create backup of {file_path}: {e}")
            return False
    
    def load_data(self, data_type: str) -> Tuple[Any, bool]:
        """
        Load data with automatic migration from legacy format if needed.
        
        Args:
            data_type: Type of data to load
            
        Returns:
            Tuple of (data, was_migrated)
        """
        if data_type not in self.schemas:
            raise ValueError(f"Unknown data type: {data_type}")
        
        schema = self.schemas[data_type]
        json_path = self._get_json_path(data_type)
        
        # Try to load from JSON first
        if path.exists(json_path):
            try:
                with open(json_path, 'r') as file:
                    data = json.load(file)
                
                # Validate data
                is_valid, error = schema.validate(data)
                if is_valid:
                    return data, False
                else:
                    print(f"Invalid data in {json_path}: {error}")
                    # Fall through to create default
            except Exception as e:
                print(f"Error loading {json_path}: {e}")
                # Fall through to check legacy or create default
        
        # Check for legacy file to migrate
        legacy_path = self._get_legacy_path(data_type)
        if path.exists(legacy_path):
            try:
                with open(legacy_path, 'rb') as file:
                    legacy_data = pickle.load(file)
                
                # Migrate to new format
                migrated_data = schema.migrate_from_legacy(legacy_data)
                
                # Save migrated data
                success, error = self.save_data(data_type, migrated_data)
                if success:
                    print(f"Migrated {legacy_path} to {json_path}")
                    return migrated_data, True
                else:
                    print(f"Failed to save migrated data: {error}")
            except Exception as e:
                print(f"Error migrating {legacy_path}: {e}")
        
        # Return default data
        default_data = schema.get_default()
        return default_data, False
    
    def save_data(self, data_type: str, data: Any) -> Tuple[bool, str]:
        """
        Save data with validation and backup.
        
        Args:
            data_type: Type of data to save
            data: Data to save
            
        Returns:
            Tuple of (success, error_message)
        """
        if data_type not in self.schemas:
            return False, f"Unknown data type: {data_type}"
        
        schema = self.schemas[data_type]
        
        # Validate data
        is_valid, error = schema.validate(data)
        if not is_valid:
            return False, f"Validation failed: {error}"
        
        json_path = self._get_json_path(data_type)
        
        # Create backup of existing file
        if not self._create_backup(json_path):
            return False, "Failed to create backup"
        
        try:
            # Update timestamp if data has it
            if isinstance(data, dict) and "last_updated" in data:
                data["last_updated"] = datetime.now().isoformat()
            
            # Save to JSON with pretty formatting
            with open(json_path, 'w') as file:
                json.dump(data, file, indent=2, sort_keys=True)
            
            return True, ""
            
        except Exception as e:
            return False, f"Failed to save file: {e}"
    
    def get_thread_channels(self) -> Set[int]:
        """Get set of thread channel IDs."""
        data, _ = self.load_data("thread_channels")
        return set(data.get("channels", []))
    
    def set_thread_channels(self, channels: Set[int]) -> bool:
        """Save set of thread channel IDs."""
        data, _ = self.load_data("thread_channels")
        data["channels"] = list(channels)
        data["metadata"]["total_channels"] = len(channels)
        success, _ = self.save_data("thread_channels", data)
        return success
    
    def add_thread_channel(self, channel_id: int) -> bool:
        """Add a thread channel."""
        channels = self.get_thread_channels()
        if channel_id in channels:
            return False
        channels.add(channel_id)
        return self.set_thread_channels(channels)
    
    def remove_thread_channel(self, channel_id: int) -> bool:
        """Remove a thread channel."""
        channels = self.get_thread_channels()
        if channel_id not in channels:
            return False
        channels.remove(channel_id)
        return self.set_thread_channels(channels)
    
    def get_poll_channels(self) -> Set[int]:
        """Get set of poll channel IDs."""
        data, _ = self.load_data("poll_channels")
        return set(data.get("channels", []))
    
    def set_poll_channels(self, channels: Set[int]) -> bool:
        """Save set of poll channel IDs."""
        data, _ = self.load_data("poll_channels")
        data["channels"] = list(channels)
        data["metadata"]["total_channels"] = len(channels)
        success, _ = self.save_data("poll_channels", data)
        return success
    
    def add_poll_channel(self, channel_id: int) -> bool:
        """Add a poll channel."""
        channels = self.get_poll_channels()
        if channel_id in channels:
            return False
        channels.add(channel_id)
        return self.set_poll_channels(channels)
    
    def remove_poll_channel(self, channel_id: int) -> bool:
        """Remove a poll channel."""
        channels = self.get_poll_channels()
        if channel_id not in channels:
            return False
        channels.remove(channel_id)
        return self.set_poll_channels(channels)
    
    def clear_thread_channels(self) -> bool:
        """Clear all thread channels."""
        return self.set_thread_channels(set())
    
    def store_api_key(self, service_name: str, api_key: str) -> bool:
        """
        Store an encrypted API key for a service.
        
        Args:
            service_name: Name of the service (e.g., 'deepseek')
            api_key: The API key to store
            
        Returns:
            True if successful
        """
        data, _ = self.load_data("api_keys")
        
        # Encrypt the API key
        encrypted_key = self._encryption_key.encrypt(api_key.encode()).decode()
        
        # Store the encrypted key
        data["keys"][service_name.lower()] = {
            "encrypted_key": encrypted_key,
            "created_at": datetime.now().isoformat()
        }
        data["metadata"]["total_keys"] = len(data["keys"])
        
        success, error = self.save_data("api_keys", data)
        return success
    
    def get_api_key(self, service_name: str) -> Optional[str]:
        """
        Retrieve and decrypt an API key for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Decrypted API key or None if not found
        """
        data, _ = self.load_data("api_keys")
        
        service_key = service_name.lower()
        if service_key not in data["keys"]:
            return None
        
        try:
            encrypted_key = data["keys"][service_key]["encrypted_key"]
            decrypted_key = self._encryption_key.decrypt(encrypted_key.encode()).decode()
            return decrypted_key
        except Exception as e:
            print(f"Error decrypting API key for {service_name}: {e}")
            return None
    
    def list_api_keys(self) -> List[str]:
        """List all stored API key service names."""
        data, _ = self.load_data("api_keys")
        return list(data["keys"].keys())
    
    def remove_api_key(self, service_name: str) -> bool:
        """
        Remove an API key for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if removed, False if not found
        """
        data, _ = self.load_data("api_keys")
        
        service_key = service_name.lower()
        if service_key not in data["keys"]:
            return False
        
        del data["keys"][service_key]
        data["metadata"]["total_keys"] = len(data["keys"])
        
        success, error = self.save_data("api_keys", data)
        return success
    
    def has_legacy_files(self) -> List[str]:
        """Check for legacy files that need migration."""
        legacy_files = []
        for data_type in self.schemas.keys():
            if data_type == "api_keys":  # Skip API keys as it's new
                continue
            legacy_path = self._get_legacy_path(data_type)
            if path.exists(legacy_path):
                legacy_files.append(legacy_path)
        return legacy_files
    
    def migrate_all_legacy_files(self) -> Dict[str, bool]:
        """Migrate all found legacy files."""
        results = {}
        for data_type in self.schemas.keys():
            if data_type == "api_keys":  # Skip API keys as it's new
                continue
            legacy_path = self._get_legacy_path(data_type)
            if path.exists(legacy_path):
                try:
                    data, was_migrated = self.load_data(data_type)
                    results[legacy_path] = was_migrated
                except Exception as e:
                    print(f"Failed to migrate {legacy_path}: {e}")
                    results[legacy_path] = False
        return results
    
    def validate_all_data(self) -> Dict[str, Tuple[bool, str]]:
        """Validate all data files."""
        results = {}
        for data_type in self.schemas.keys():
            try:
                data, _ = self.load_data(data_type)
                schema = self.schemas[data_type]
                is_valid, error = schema.validate(data)
                results[data_type] = (is_valid, error)
            except Exception as e:
                results[data_type] = (False, str(e))
        return results
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of all data."""
        summary = {}
        for data_type in self.schemas.keys():
            try:
                data, was_migrated = self.load_data(data_type)
                summary[data_type] = {
                    "exists": True,
                    "was_migrated": was_migrated,
                    "last_updated": data.get("last_updated", "Unknown"),
                    "item_count": len(data.get("channels", data.get("keys", data.keys() if isinstance(data, dict) else []))),
                }
            except Exception as e:
                summary[data_type] = {
                    "exists": False,
                    "error": str(e)
                }
        return summary