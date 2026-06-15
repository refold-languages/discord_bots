"""
Services package for Refold Helper Bot.
Contains business logic classes separated from Discord API interactions.
"""

from .base_service import BaseService
from .role_service import RoleService
from .project_service import ProjectService, ProjectData
from .thread_service import ThreadService, ThreadMessageData
from .migration_service import MigrationService, MigrationReport
from .course_service import CourseService, StudentRecord, CourseConfig
from .homework_service import HomeworkService, HomeworkAssignment
from .youtube_service import YouTubeService, VideoInfo, ProcessingProgress
from .honeypot_service import HoneypotService
from .spam_detection_service import (
    SpamDetectionService,
    ACTION_NONE,
    ACTION_TIMEOUT,
    ACTION_BAN,
)
from .enforcement_state import EnforcementState, enforcement_state

__all__ = [
    'BaseService',
    'RoleService', 
    'ProjectService',
    'ProjectData',
    'ThreadService',
    'ThreadMessageData',
    'MigrationService',
    'MigrationReport',
    'CourseService',
    'StudentRecord',
    'CourseConfig',
    'HomeworkService',
    'HomeworkAssignment',
    'YouTubeService',
    'VideoInfo',
    'ProcessingProgress',
    'HoneypotService',
    'SpamDetectionService',
    'ACTION_NONE',
    'ACTION_TIMEOUT',
    'ACTION_BAN',
    'EnforcementState',
    'enforcement_state',
]