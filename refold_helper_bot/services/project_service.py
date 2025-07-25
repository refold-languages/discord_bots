"""
Project service for Refold Helper Bot.
Handles community project management business logic with comprehensive logging and error handling.
"""

import json
from os import path
from typing import Dict, List, Optional, Tuple

from .base_service import BaseService
from config.constants import PROJECTS_FILE
from utils import get_logger, performance_monitor, DataError, ValidationError, safe_execute


class ProjectData:
    """Data class for project information."""
    
    def __init__(self, name: str, leader: str, description: str):
        self.name = name.lower().strip()
        self.leader = leader.strip()
        self.description = description.strip()
    
    def to_dict(self) -> List[str]:
        """Convert to format used in JSON storage."""
        return [self.leader, self.description]
    
    @classmethod
    def from_dict(cls, name: str, data: List[str]) -> 'ProjectData':
        """Create from JSON storage format."""
        if not isinstance(data, list) or len(data) != 2:
            raise ValidationError(f"Invalid project data format for {name}", field="project_data", value=data)
        return cls(name, data[0], data[1])


class ProjectService(BaseService):
    """Service for managing community projects with comprehensive monitoring."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.project')
        self._projects: Dict[str, ProjectData] = {}
    
    def initialize(self) -> None:
        """Initialize the project service by loading existing projects."""
        super().initialize()
        self.logger.info("project_service_initializing")
        
        try:
            self._load_projects()  # Made synchronous
            self.logger.info("project_service_initialized", 
                           project_count=len(self._projects))
        except Exception as e:
            self.logger.error("project_service_initialization_failed", 
                            error=str(e), 
                            error_type=type(e).__name__)
            raise
    
    def _load_projects(self) -> None:  # Changed from async to sync
        """Load projects from JSON file with comprehensive error handling."""
        try:
            if path.exists(PROJECTS_FILE):
                with open(PROJECTS_FILE, 'r') as file:
                    data = json.load(file)
                
                # Validate and load each project
                loaded_count = 0
                error_count = 0
                
                for name, project_data in data.items():
                    try:
                        self._projects[name] = ProjectData.from_dict(name, project_data)
                        loaded_count += 1
                    except ValidationError as e:
                        self.logger.warning("invalid_project_data_skipped",
                                          project_name=name,
                                          error=str(e))
                        error_count += 1
                
                self.logger.info("projects_loaded_from_file",
                               file_path=PROJECTS_FILE,
                               loaded_count=loaded_count,
                               error_count=error_count)
            else:
                self._projects = {}
                self.logger.info("no_projects_file_found", 
                               file_path=PROJECTS_FILE,
                               creating_empty_state=True)
                
        except FileNotFoundError:
            self._projects = {}
            self.logger.info("projects_file_not_found", 
                           file_path=PROJECTS_FILE)
        except json.JSONDecodeError as e:
            self.logger.error("projects_file_invalid_json",
                            file_path=PROJECTS_FILE,
                            error=str(e),
                            line=getattr(e, 'lineno', None),
                            column=getattr(e, 'colno', None))
            raise DataError(f"Projects file contains invalid JSON: {str(e)}", 
                          operation="load", 
                          data_type="projects")
        except PermissionError as e:
            self.logger.error("projects_file_permission_denied",
                            file_path=PROJECTS_FILE,
                            error=str(e))
            raise DataError(f"Permission denied accessing projects file: {str(e)}",
                          operation="load",
                          data_type="projects")
        except Exception as e:
            self.logger.error("unexpected_error_loading_projects",
                            file_path=PROJECTS_FILE,
                            error=str(e),
                            error_type=type(e).__name__)
            raise DataError(f"Unexpected error loading projects: {str(e)}",
                          operation="load",
                          data_type="projects")
    
    @safe_execute("save_projects")
    async def _save_projects(self) -> bool:
        """Save projects to JSON file with comprehensive error handling."""
        async with performance_monitor.track("save_projects", project_count=len(self._projects)):
            try:
                data = {
                    name: project.to_dict()
                    for name, project in self._projects.items()
                }
                
                with open(PROJECTS_FILE, 'w') as file:
                    json.dump(data, file, indent=2)
                
                self.logger.info("projects_saved_successfully",
                               file_path=PROJECTS_FILE,
                               project_count=len(self._projects))
                return True
                
            except PermissionError as e:
                self.logger.error("projects_save_permission_denied",
                                file_path=PROJECTS_FILE,
                                error=str(e))
                raise DataError(f"Permission denied saving projects file: {str(e)}",
                              operation="save",
                              data_type="projects")
            except OSError as e:
                self.logger.error("projects_save_os_error",
                                file_path=PROJECTS_FILE,
                                error=str(e))
                raise DataError(f"System error saving projects file: {str(e)}",
                              operation="save",
                              data_type="projects")
            except Exception as e:
                self.logger.error("unexpected_error_saving_projects",
                                file_path=PROJECTS_FILE,
                                error=str(e),
                                error_type=type(e).__name__)
                raise DataError(f"Unexpected error saving projects: {str(e)}",
                              operation="save",
                              data_type="projects")
    
    async def create_project(self, name: str, leader: str, description: str) -> Tuple[bool, str]:
        """
        Create a new project with comprehensive validation and error handling.
        
        Args:
            name: Project name
            leader: Project leader name
            description: Project description
            
        Returns:
            Tuple of (success, message)
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("create_project", project_name=name):
            self.logger.info("project_creation_requested",
                           project_name=name,
                           leader=leader,
                           description_length=len(description))
            
            # Validate input
            if not name or not leader or not description:
                error_msg = "All fields (name, leader, description) are required"
                self.logger.warning("project_creation_validation_failed",
                                  project_name=name,
                                  error=error_msg,
                                  missing_fields=[
                                      field for field, value in [
                                          ("name", name), ("leader", leader), ("description", description)
                                      ] if not value
                                  ])
                return False, error_msg
            
            # Sanitize name
            clean_name = self.sanitize_string(name.lower())
            if not clean_name:
                error_msg = "Invalid project name"
                self.logger.warning("project_creation_invalid_name",
                                  original_name=name,
                                  sanitized_name=clean_name)
                return False, error_msg
            
            # Check if project already exists
            if clean_name in self._projects:
                error_msg = "A project with this name already exists"
                self.logger.warning("project_creation_duplicate_name",
                                  project_name=clean_name,
                                  existing_leader=self._projects[clean_name].leader)
                return False, error_msg
            
            # Create project
            try:
                project = ProjectData(clean_name, leader, description)
                self._projects[clean_name] = project
                
                # Save to file
                await self._save_projects()
                
                self.logger.info("project_created_successfully",
                               project_name=clean_name,
                               leader=leader,
                               description_length=len(description),
                               total_projects=len(self._projects))
                
                return True, f"Project '{clean_name}' created successfully"
                
            except DataError:
                # Rollback on save failure
                if clean_name in self._projects:
                    del self._projects[clean_name]
                raise
            except Exception as e:
                # Rollback on unexpected failure
                if clean_name in self._projects:
                    del self._projects[clean_name]
                
                self.logger.error("project_creation_unexpected_error",
                                project_name=clean_name,
                                error=str(e),
                                error_type=type(e).__name__)
                return False, "Failed to create project due to an unexpected error"
    
    def get_project(self, name: str) -> Optional[ProjectData]:
        """
        Get project by name with logging.
        
        Args:
            name: Project name to look up
            
        Returns:
            ProjectData if found, None otherwise
        """
        self._ensure_initialized()
        clean_name = name.lower().strip()
        
        project = self._projects.get(clean_name)
        
        self.logger.debug("project_lookup",
                         project_name=clean_name,
                         found=project is not None)
        
        return project
    
    def project_exists(self, name: str) -> bool:
        """
        Check if a project exists with logging.
        
        Args:
            name: Project name to check
            
        Returns:
            True if project exists
        """
        self._ensure_initialized()
        clean_name = name.lower().strip()
        exists = clean_name in self._projects
        
        self.logger.debug("project_existence_check",
                         project_name=clean_name,
                         exists=exists)
        
        return exists
    
    def get_all_projects(self) -> Dict[str, ProjectData]:
        """
        Get all projects with performance tracking.
        
        Returns:
            Dictionary of project name to ProjectData
        """
        self._ensure_initialized()
        
        self.logger.debug("all_projects_requested", 
                         project_count=len(self._projects))
        
        return self._projects.copy()
    
    async def delete_project(self, name: str) -> Tuple[bool, str]:
        """
        Delete a project with comprehensive error handling.
        
        Args:
            name: Project name to delete
            
        Returns:
            Tuple of (success, message)
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("delete_project", project_name=name):
            clean_name = name.lower().strip()
            
            self.logger.info("project_deletion_requested",
                           project_name=clean_name)
            
            if clean_name not in self._projects:
                error_msg = "Project not found"
                self.logger.warning("project_deletion_not_found",
                                  project_name=clean_name)
                return False, error_msg
            
            # Remove project
            deleted_project = self._projects.pop(clean_name)
            
            try:
                # Save changes
                await self._save_projects()
                
                self.logger.info("project_deleted_successfully",
                               project_name=clean_name,
                               leader=deleted_project.leader,
                               remaining_projects=len(self._projects))
                
                return True, f"Project '{clean_name}' archived successfully"
                
            except DataError:
                # Rollback on save failure
                self._projects[clean_name] = deleted_project
                self.logger.error("project_deletion_rollback",
                                project_name=clean_name,
                                reason="save_failed")
                raise
            except Exception as e:
                # Rollback on unexpected failure
                self._projects[clean_name] = deleted_project
                self.logger.error("project_deletion_unexpected_error",
                                project_name=clean_name,
                                error=str(e),
                                error_type=type(e).__name__)
                return False, "Failed to delete project due to an unexpected error"
    
    async def update_project(self, name: str, leader: str = None, description: str = None) -> Tuple[bool, str]:
        """
        Update an existing project with validation and error handling.
        
        Args:
            name: Project name to update
            leader: New leader name (optional)
            description: New description (optional)
            
        Returns:
            Tuple of (success, message)
        """
        self._ensure_initialized()
        
        async with performance_monitor.track("update_project", project_name=name):
            clean_name = name.lower().strip()
            
            self.logger.info("project_update_requested",
                           project_name=clean_name,
                           updating_leader=leader is not None,
                           updating_description=description is not None)
            
            if clean_name not in self._projects:
                error_msg = "Project not found"
                self.logger.warning("project_update_not_found",
                                  project_name=clean_name)
                return False, error_msg
            
            project = self._projects[clean_name]
            old_leader = project.leader
            old_description = project.description
            
            # Update fields if provided
            if leader is not None:
                project.leader = leader.strip()
            if description is not None:
                project.description = description.strip()
            
            try:
                # Save changes
                await self._save_projects()
                
                self.logger.info("project_updated_successfully",
                               project_name=clean_name,
                               leader_changed=old_leader != project.leader,
                               description_changed=old_description != project.description,
                               new_leader=project.leader,
                               description_length=len(project.description))
                
                return True, f"Project '{clean_name}' updated successfully"
                
            except DataError:
                # Rollback changes
                project.leader = old_leader
                project.description = old_description
                self.logger.error("project_update_rollback",
                                project_name=clean_name,
                                reason="save_failed")
                raise
            except Exception as e:
                # Rollback changes
                project.leader = old_leader
                project.description = old_description
                self.logger.error("project_update_unexpected_error",
                                project_name=clean_name,
                                error=str(e),
                                error_type=type(e).__name__)
                return False, "Failed to update project due to an unexpected error"
    
    def validate_project_name(self, name: str) -> Tuple[bool, str]:
        """
        Validate a project name with detailed logging.
        
        Args:
            name: Project name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        self.logger.debug("project_name_validation_requested", project_name=name)
        
        if not name or not isinstance(name, str):
            self.logger.debug("project_name_validation_failed", 
                            project_name=name, 
                            reason="empty_or_not_string")
            return False, "Project name is required"
        
        clean_name = name.strip()
        
        if len(clean_name) < 2:
            self.logger.debug("project_name_validation_failed",
                            project_name=clean_name,
                            reason="too_short",
                            length=len(clean_name))
            return False, "Project name must be at least 2 characters"
        
        if len(clean_name) > 50:
            self.logger.debug("project_name_validation_failed",
                            project_name=clean_name,
                            reason="too_long",
                            length=len(clean_name))
            return False, "Project name must be 50 characters or less"
        
        # Check for problematic characters
        problematic_chars = ['/', '\\', '<', '>', ':', '"', '|', '?', '*']
        found_chars = [char for char in problematic_chars if char in clean_name]
        if found_chars:
            self.logger.debug("project_name_validation_failed",
                            project_name=clean_name,
                            reason="invalid_characters",
                            invalid_chars=found_chars)
            return False, "Project name contains invalid characters"
        
        self.logger.debug("project_name_validation_passed", project_name=clean_name)
        return True, ""
    
    def get_project_count(self) -> int:
        """
        Get total number of active projects.
        
        Returns:
            Number of projects
        """
        self._ensure_initialized()
        count = len(self._projects)
        self.logger.debug("project_count_requested", count=count)
        return count
    
    def search_projects(self, query: str) -> List[ProjectData]:
        """
        Search projects by name, leader, or description with performance tracking.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching ProjectData objects
        """
        self._ensure_initialized()
        
        self.logger.debug("project_search_requested", 
                        query=query,
                        total_projects=len(self._projects))
        
        if not query:
            matches = list(self._projects.values())
        else:
            query_lower = query.lower()
            matches = []
            
            for project in self._projects.values():
                if (query_lower in project.name or 
                    query_lower in project.leader.lower() or 
                    query_lower in project.description.lower()):
                    matches.append(project)
        
        self.logger.info("project_search_completed",
                       query=query,
                       matches_found=len(matches),
                       total_searched=len(self._projects))
        
        return matches
    
    def get_projects_by_leader(self, leader: str) -> List[ProjectData]:
        """
        Get all projects led by a specific person.
        
        Args:
            leader: Leader name to search for
            
        Returns:
            List of ProjectData objects
        """
        self._ensure_initialized()
        
        self.logger.debug("projects_by_leader_requested", leader=leader)
        
        leader_lower = leader.lower()
        matches = [
            project for project in self._projects.values()
            if leader_lower in project.leader.lower()
        ]
        
        self.logger.info("projects_by_leader_completed",
                        leader=leader,
                        matches_found=len(matches))
        
        return matches