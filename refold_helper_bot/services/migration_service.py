"""
Migration service for Refold Helper Bot.
Handles data format migrations and legacy file conversion.
"""

import shutil
from datetime import datetime
from os import path
from typing import Dict, List, Tuple

from .base_service import BaseService
from core import DataManager


class MigrationReport:
    """Report of migration results."""
    
    def __init__(self):
        self.files_found: List[str] = []
        self.files_migrated: List[str] = []
        self.files_failed: List[str] = []
        self.errors: List[str] = []
        self.backups_created: List[str] = []
    
    @property
    def success_count(self) -> int:
        return len(self.files_migrated)
    
    @property
    def failure_count(self) -> int:
        return len(self.files_failed)
    
    @property
    def total_found(self) -> int:
        return len(self.files_found)
    
    def add_success(self, filename: str):
        self.files_migrated.append(filename)
    
    def add_failure(self, filename: str, error: str):
        self.files_failed.append(filename)
        self.errors.append(f"{filename}: {error}")
    
    def add_backup(self, backup_path: str):
        self.backups_created.append(backup_path)


class MigrationService(BaseService):
    """Service for handling data migrations and legacy file conversion."""
    
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()
    
    def initialize(self) -> None:
        """Initialize the migration service."""
        super().initialize()
        self.data_manager  # DataManager initializes itself
    
    def scan_for_legacy_files(self) -> List[str]:
        """
        Scan for legacy files that need migration.
        
        Returns:
            List of legacy file paths found
        """
        self._ensure_initialized()
        return self.data_manager.has_legacy_files()
    
    def create_legacy_backups(self, legacy_files: List[str]) -> List[str]:
        """
        Create backups of legacy files before migration.
        
        Args:
            legacy_files: List of legacy file paths
            
        Returns:
            List of backup file paths created
        """
        backups = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for file_path in legacy_files:
            if path.exists(file_path):
                try:
                    backup_path = f"{file_path}.backup_{timestamp}"
                    shutil.copy2(file_path, backup_path)
                    backups.append(backup_path)
                except Exception as e:
                    print(f"Failed to backup {file_path}: {e}")
        
        return backups
    
    def migrate_single_file(self, data_type: str) -> Tuple[bool, str]:
        """
        Migrate a single data type from legacy format.
        
        Args:
            data_type: Type of data to migrate
            
        Returns:
            Tuple of (success, message)
        """
        self._ensure_initialized()
        
        try:
            data, was_migrated = self.data_manager.load_data(data_type)
            if was_migrated:
                return True, f"Successfully migrated {data_type}"
            else:
                return True, f"No migration needed for {data_type}"
        except Exception as e:
            return False, f"Migration failed for {data_type}: {e}"
    
    def migrate_all_files(self) -> MigrationReport:
        """
        Migrate all legacy files to new format.
        
        Returns:
            MigrationReport with detailed results
        """
        self._ensure_initialized()
        
        report = MigrationReport()
        
        # Scan for legacy files
        legacy_files = self.scan_for_legacy_files()
        report.files_found = legacy_files.copy()
        
        if not legacy_files:
            return report
        
        # Create backups
        backups = self.create_legacy_backups(legacy_files)
        report.backups_created = backups
        
        # Migrate each data type
        migration_results = self.data_manager.migrate_all_legacy_files()
        
        for file_path, success in migration_results.items():
            if success:
                report.add_success(file_path)
            else:
                report.add_failure(file_path, "Migration returned False")
        
        return report
    
    def validate_migration(self) -> Dict[str, Tuple[bool, str]]:
        """
        Validate that all migrated data is correct.
        
        Returns:
            Dictionary of validation results per data type
        """
        self._ensure_initialized()
        return self.data_manager.validate_all_data()
    
    def get_migration_status(self) -> Dict[str, any]:
        """
        Get current migration status and data summary.
        
        Returns:
            Dictionary with migration status information
        """
        self._ensure_initialized()
        
        legacy_files = self.scan_for_legacy_files()
        data_summary = self.data_manager.get_data_summary()
        validation_results = self.validate_migration()
        
        return {
            "legacy_files_found": legacy_files,
            "needs_migration": len(legacy_files) > 0,
            "data_summary": data_summary,
            "validation_results": validation_results,
            "all_valid": all(valid for valid, _ in validation_results.values())
        }
    
    def cleanup_legacy_files(self, confirm: bool = False) -> Tuple[bool, str]:
        """
        Clean up legacy files after successful migration.
        
        Args:
            confirm: Must be True to actually delete files
            
        Returns:
            Tuple of (success, message)
        """
        if not confirm:
            return False, "Confirmation required to delete legacy files"
        
        self._ensure_initialized()
        
        legacy_files = self.scan_for_legacy_files()
        if not legacy_files:
            return True, "No legacy files to clean up"
        
        # Validate that migration was successful first
        validation_results = self.validate_migration()
        if not all(valid for valid, _ in validation_results.values()):
            return False, "Cannot cleanup: migration validation failed"
        
        deleted_files = []
        failed_deletions = []
        
        for file_path in legacy_files:
            if path.exists(file_path):
                try:
                    # Move to backup instead of delete for safety
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    archived_path = f"{file_path}.archived_{timestamp}"
                    shutil.move(file_path, archived_path)
                    deleted_files.append(f"{file_path} -> {archived_path}")
                except Exception as e:
                    failed_deletions.append(f"{file_path}: {e}")
        
        if failed_deletions:
            return False, f"Some files failed to archive: {failed_deletions}"
        
        return True, f"Archived {len(deleted_files)} legacy files: {deleted_files}"
    
    def force_recreate_data_files(self) -> Dict[str, bool]:
        """
        Force recreate all data files with default values.
        WARNING: This will overwrite existing data!
        
        Returns:
            Dictionary of results per data type
        """
        self._ensure_initialized()
        
        results = {}
        
        # Get all data types from schemas
        for data_type in self.data_manager.schemas.keys():
            try:
                schema = self.data_manager.schemas[data_type]
                default_data = schema.get_default()
                success, error = self.data_manager.save_data(data_type, default_data)
                results[data_type] = success
                if not success:
                    print(f"Failed to recreate {data_type}: {error}")
            except Exception as e:
                results[data_type] = False
                print(f"Error recreating {data_type}: {e}")
        
        return results