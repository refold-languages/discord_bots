"""
Course service for Refold Helper Bot.
Handles course configurations and student roster management.
"""

import csv
import pytz
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import discord

from .base_service import BaseService
from core import DataManager
from utils import get_logger, performance_monitor, safe_execute, ValidationError, DataError

@dataclass
class StudentRecord:
    email: str
    name: str
    discord_handle: str
    course_name: str
    enrolled_date: str = ""
    status: str = "pending"
    discord_id: Optional[int] = None
    
    def __post_init__(self):
        # Normalize discord handle for matching
        self.discord_handle = self.discord_handle.lower().strip()

@dataclass 
class CourseConfig:
    name: str
    role_id: int
    category_id: int
    channels: List[str] = None
    welcome_message: str = ""
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = []

@dataclass
class StudentActivity:
    student: StudentRecord
    total_messages: int
    messages_last_week: int
    last_message_date: Optional[datetime] = None
    member_since: Optional[datetime] = None
    
    @property
    def activity_tier(self) -> str:
        """Determine activity tier based on message counts."""
        if self.messages_last_week == 0:
            return "At Risk"
        elif self.messages_last_week < 3:
            return "Low Activity" 
        else:
            return "Active"

class CourseService(BaseService):
    """Service for managing course configurations and student rosters."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.course')
        self.data_manager = DataManager()
        self._students: List[StudentRecord] = []
        self._courses: Dict[str, CourseConfig] = {}
        
        # Servers that can use course features
        self.ALLOWED_COURSE_SERVERS = {
            1093991079197560912,  # Production course server
            778331995297808438,   # Test server
        }
        
        # Backend admin channels that can upload rosters
        self.BACKEND_CHANNELS = {1121195017097199646, 819431673954959400}
    
    def initialize(self) -> None:
        super().initialize()
        self.logger.info("course_service_initializing")
        self._load_course_config()
    
    def is_course_server(self, guild_id: int) -> bool:
        """Check if a guild is allowed to use course features."""
        return guild_id in self.ALLOWED_COURSE_SERVERS
    
    def is_backend_channel(self, channel_id: int) -> bool:
        """Check if a channel is allowed to upload rosters."""
        return channel_id in self.BACKEND_CHANNELS
    
    def _normalize_course_name(self, name: str) -> str:
        """Normalize course name for consistent key handling."""
        # Strip quotes that Discord might include, then normalize
        cleaned = name.strip().strip('"').strip("'").strip()
        return cleaned.lower()
    
    def _load_course_config(self) -> None:
        """Load course configurations from data manager."""
        try:
            data, _ = self.data_manager.load_data("course_config")
            self._courses = {}
            
            for course_name, config_data in data.get("courses", {}).items():
                # Use normalized name as key, but keep original name in config
                normalized_key = self._normalize_course_name(course_name)
                self._courses[normalized_key] = CourseConfig(
                    name=course_name,  # Keep original case for display
                    **config_data
                )
            
            self.logger.info("course_config_loaded", 
                           course_count=len(self._courses),
                           course_names=list(self._courses.keys()))
        except Exception as e:
            self.logger.error("course_config_load_failed", error=str(e))
            self._courses = {}
    
    @safe_execute("save_course_config")
    async def _save_course_config(self) -> bool:
        """Save course configurations to data manager."""
        data, _ = self.data_manager.load_data("course_config")
        
        # Update courses data - use original case names as JSON keys for readability
        data["courses"] = {
            config.name: {  # Use original case for JSON key
                "role_id": config.role_id,
                "category_id": config.category_id,
                "channels": config.channels,
                "welcome_message": config.welcome_message
            }
            for config in self._courses.values()
        }
        data["metadata"]["total_courses"] = len(self._courses)
        
        success, error = self.data_manager.save_data("course_config", data)
        if not success:
            raise DataError(f"Failed to save course config: {error}")
        
        return True
    
    @safe_execute("add_course")
    async def add_course(self, name: str, role_id: int, category_id: int, 
                        channels: List[str] = None, welcome_message: str = "") -> Tuple[bool, str]:
        """Add a new course configuration."""
        clean_name = name.strip().strip('"').strip("'").strip()  # Remove quotes
        if not clean_name:
            return False, "Course name cannot be empty"
        
        normalized_key = self._normalize_course_name(clean_name)
        
        if normalized_key in self._courses:
            return False, f"Course '{clean_name}' already exists"
        
        # Validate IDs are positive integers
        if role_id <= 0 or category_id <= 0:
            return False, "Role ID and Category ID must be positive integers"
        
        course_config = CourseConfig(
            name=clean_name,  # Keep original case for display
            role_id=role_id,
            category_id=category_id,
            channels=channels or [],
            welcome_message=welcome_message
        )
        
        self._courses[normalized_key] = course_config
        await self._save_course_config()
        
        self.logger.info("course_added", 
                        course_name=clean_name,
                        normalized_key=normalized_key,
                        role_id=role_id,
                        category_id=category_id)
        
        return True, f"Course '{clean_name}' added successfully"
    
    @safe_execute("remove_course")
    async def remove_course(self, name: str) -> Tuple[bool, str]:
        """Remove a course configuration."""
        normalized_key = self._normalize_course_name(name)
        
        if normalized_key not in self._courses:
            return False, f"Course '{name}' not found"
        
        # Get the course info before removing for logging
        removed_course = self._courses[normalized_key]
        
        # Remove from memory
        del self._courses[normalized_key]
        
        # Save updated config
        await self._save_course_config()
        
        self.logger.info("course_removed",
                        course_name=removed_course.name,
                        normalized_key=normalized_key,
                        role_id=removed_course.role_id,
                        category_id=removed_course.category_id)
        
        return True, f"Course '{removed_course.name}' removed successfully"

    def get_course(self, name: str) -> Optional[CourseConfig]:
        """Get course configuration by name."""
        normalized_key = self._normalize_course_name(name)
        course = self._courses.get(normalized_key)
        
        self.logger.debug("course_lookup",
                         requested_name=name,
                         normalized_key=normalized_key,
                         found=course is not None,
                         available_keys=list(self._courses.keys()))
        
        return course
    
    def get_all_courses(self) -> Dict[str, CourseConfig]:
        """Get all course configurations."""
        return self._courses.copy()
    
    def get_course_count(self) -> int:
        """Get total number of configured courses."""
        return len(self._courses)
    
    def get_category_channels(self, guild, category_id: int) -> List[Dict[str, Any]]:
        """Get all channels that belong to a specific category."""
        channels = []
        
        for channel in guild.channels:
            if hasattr(channel, 'category_id') and channel.category_id == category_id:
                channels.append({
                    'id': channel.id,
                    'name': channel.name,
                    'type': str(channel.type).replace('ChannelType.', ''),
                    'position': getattr(channel, 'position', 0),
                    'channel_obj': channel
                })
        
        # Sort by position for consistent ordering
        channels.sort(key=lambda x: x['position'])
        return channels
    
    @safe_execute("load_roster")
    async def load_roster_from_csv(self, file_path: str) -> Tuple[bool, str]:
        """Load student roster from CSV file."""
        try:
            students = []
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                required_columns = {'email', 'name', 'discord_handle', 'course_name'}
                if not required_columns.issubset(reader.fieldnames):
                    missing = required_columns - set(reader.fieldnames)
                    return False, f"Missing required columns: {missing}"
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Validate required fields
                        for field in required_columns:
                            if not row.get(field, '').strip():
                                return False, f"Row {row_num}: {field} cannot be empty"
                        
                        # Check if course exists
                        course_name = row['course_name'].strip()
                        if not self.get_course(course_name):
                            return False, f"Row {row_num}: Course '{course_name}' not configured. Use `!course add` to create it first."
                        
                        student = StudentRecord(
                            email=row['email'].strip(),
                            name=row['name'].strip(),
                            discord_handle=row['discord_handle'].strip(),
                            course_name=course_name,
                            enrolled_date=row.get('enrolled_date', '').strip(),
                            status=row.get('status', 'pending').strip()
                        )
                        students.append(student)
                        
                    except Exception as e:
                        return False, f"Row {row_num}: {str(e)}"
            
            self._students = students
            
            self.logger.info("roster_loaded_from_csv",
                           file_path=file_path,
                           student_count=len(students))
            
            return True, f"Loaded {len(students)} students from roster"
            
        except FileNotFoundError:
            return False, f"File not found: {file_path}"
        except Exception as e:
            self.logger.error("roster_load_failed", file_path=file_path, error=str(e))
            return False, f"Failed to load roster: {str(e)}"
    
    @safe_execute("load_roster_from_text")
    async def load_roster_from_text(self, csv_text: str) -> Tuple[bool, str]:
        """Load student roster from CSV text content."""
        try:
            students = []
            lines = csv_text.strip().split('\n')
            reader = csv.DictReader(lines)
            
            required_columns = {'email', 'name', 'discord_handle', 'course_name'}
            if not required_columns.issubset(reader.fieldnames):
                missing = required_columns - set(reader.fieldnames)
                return False, f"Missing required columns: {missing}"
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Validate required fields
                    for field in required_columns:
                        if not row.get(field, '').strip():
                            return False, f"Row {row_num}: {field} cannot be empty"
                    
                    # Check if course exists
                    course_name = row['course_name'].strip()
                    if not self.get_course(course_name):
                        return False, f"Row {row_num}: Course '{course_name}' not configured. Use `!course add` to create it first."
                    
                    student = StudentRecord(
                        email=row['email'].strip(),
                        name=row['name'].strip(),
                        discord_handle=row['discord_handle'].strip(),
                        course_name=course_name,
                        enrolled_date=row.get('enrolled_date', '').strip(),
                        status=row.get('status', 'pending').strip()
                    )
                    students.append(student)
                    
                except Exception as e:
                    return False, f"Row {row_num}: {str(e)}"
            
            self._students = students
            
            self.logger.info("roster_loaded_from_text",
                           student_count=len(students))
            
            return True, f"Loaded {len(students)} students from roster"
            
        except Exception as e:
            self.logger.error("roster_text_load_failed", error=str(e))
            return False, f"Failed to load roster: {str(e)}"
    
    def find_student_by_discord(self, discord_handle: str) -> Optional[StudentRecord]:
        """Find student by Discord handle."""
        normalized = discord_handle.lower().strip()
        for student in self._students:
            if student.discord_handle == normalized:
                return student
        return None
    
    def get_course_students(self, course_name: str) -> List[StudentRecord]:
        """Get all students for a specific course."""
        course_key = course_name.lower().strip()
        return [s for s in self._students if s.course_name.lower() == course_key]
    
    @safe_execute("update_student_discord_id")
    async def update_student_discord_id(self, discord_handle: str, discord_id: int) -> bool:
        """Update student record with Discord ID when they join."""
        student = self.find_student_by_discord(discord_handle)
        if student:
            student.discord_id = discord_id
            if student.status == "pending":
                student.status = "enrolled"
            
            self.logger.info("student_discord_id_updated",
                           discord_handle=discord_handle,
                           discord_id=discord_id,
                           course=student.course_name)
            return True
        return False
    
    def get_roster_summary(self) -> Dict[str, Any]:
        """Get summary of current roster."""
        total = len(self._students)
        by_status = {}
        by_course = {}
        
        for student in self._students:
            # Count by status
            by_status[student.status] = by_status.get(student.status, 0) + 1
            
            # Count by course
            by_course[student.course_name] = by_course.get(student.course_name, 0) + 1
        
        return {
            "total_students": total,
            "by_status": by_status,
            "by_course": by_course,
            "configured_courses": len(self._courses)
        }
    
    def get_pending_students(self) -> List[StudentRecord]:
        """Get students who haven't been assigned roles yet."""
        return [s for s in self._students if s.status == "pending"]
    
    def get_enrolled_students(self) -> List[StudentRecord]:
        """Get students who have been assigned roles."""
        return [s for s in self._students if s.status == "enrolled"]
    
    @safe_execute("health_check")
    async def run_health_check(self, guild, course_name: str, progress_callback=None) -> Tuple[bool, str, List[StudentActivity]]:
        """
        Run health check for a course by analyzing student message activity.
        
        Args:
            guild: Discord guild object
            course_name: Name of the course to check
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, message, student_activities)
        """
        try:
            course = self.get_course(course_name)
            if not course:
                return False, f"Course '{course_name}' not found", []
            
            students = self.get_course_students(course_name)
            if not students:
                # Debug info for troubleshooting
                all_students = self._students
                stored_courses = [s.course_name for s in all_students]
                return False, f"No students found in roster for course '{course_name}'. Stored courses: {stored_courses}", []
            
            # Get course channels
            channels = self.get_category_channels(guild, course.category_id)
            if not channels:
                return False, f"No channels found for course category", []
            
            # Set up time ranges properly with UTC conversion
            utc = pytz.UTC
            pacific = pytz.timezone('US/Pacific')
            now_utc = datetime.now(utc)
            now_pacific = now_utc.astimezone(pacific)
            
            # Last 7 calendar days (start of week to now) in Pacific, then convert to UTC
            days_back = 7
            week_start_pacific = now_pacific - timedelta(days=days_back)
            week_start_pacific = week_start_pacific.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start_utc = week_start_pacific.astimezone(utc)
            
            # Last 30 days for total count - convert to UTC for Discord API
            month_start_pacific = now_pacific - timedelta(days=30)
            month_start_utc = month_start_pacific.astimezone(utc)
            
            if progress_callback:
                await progress_callback(f"🔍 Scanning {len(channels)} channels for activity...")
                await progress_callback(f"📅 Time range: {month_start_pacific.strftime('%Y-%m-%d')} to {now_pacific.strftime('%Y-%m-%d')}")
            
            # Create lookup for students by discord ID and username
            student_lookup = {}
            for student in students:
                if student.discord_id:
                    student_lookup[student.discord_id] = student
                # Also add by username for matching (both normalized forms)
                student_lookup[student.discord_handle] = student
                # Add additional variations for robust matching
                if '#' in student.discord_handle:
                    # Handle old Discord usernames with discriminators
                    username_part = student.discord_handle.split('#')[0]
                    student_lookup[username_part] = student
            
            # Track message counts per student
            student_activity = {}
            for student in students:
                student_activity[student.discord_handle] = {
                    'total': 0,
                    'week': 0,
                    'last_message': None,
                    'student': student
                }
            
            # Scan each channel
            total_channels = len(channels)
            total_messages_scanned = 0
            
            for i, channel_info in enumerate(channels):
                channel = channel_info['channel_obj']
                
                if progress_callback:
                    await progress_callback(f"📊 Scanning {channel.name} ({i+1}/{total_channels})...")
                
                try:
                    # Check if we have permission to read message history
                    permissions = channel.permissions_for(guild.me)
                    if not permissions.read_message_history:
                        if progress_callback:
                            await progress_callback(f"⚠️ No permission to read {channel.name}")
                        continue
                    
                    # Scan messages in the channel with rate limiting
                    channel_message_count = 0
                    
                    # Use UTC time for Discord API call
                    async for message in channel.history(limit=1000, after=month_start_utc):
                        channel_message_count += 1
                        total_messages_scanned += 1
                        
                        if message.author.bot:
                            continue
                        
                        # Try to match message author to student
                        student = None
                        
                        # First try by Discord ID
                        if message.author.id in student_lookup:
                            student = student_lookup[message.author.id]
                        else:
                            # Try by various username formats
                            author_str = str(message.author).lower()
                            if author_str in student_lookup:
                                student = student_lookup[author_str]
                            else:
                                # Try just the username part (before #)
                                username_only = message.author.name.lower()
                                if username_only in student_lookup:
                                    student = student_lookup[username_only]
                        
                        if student:
                            activity = student_activity[student.discord_handle]
                            
                            # Count total messages (last 30 days)
                            activity['total'] += 1
                            
                            # Count messages from last week - both times are UTC now
                            if message.created_at >= week_start_utc:
                                activity['week'] += 1
                            
                            # Track most recent message
                            if not activity['last_message'] or message.created_at > activity['last_message']:
                                activity['last_message'] = message.created_at
                        
                        # Add small delay every 50 messages to avoid rate limits
                        if channel_message_count % 50 == 0:
                            await asyncio.sleep(0.1)
                    
                    # Update progress with channel results
                    if progress_callback:
                        await progress_callback(f"✅ {channel.name}: {channel_message_count} messages scanned")
                    
                    # Also scan threads in this channel (with error handling)
                    if hasattr(channel, 'threads'):
                        try:
                            threads = []
                            
                            # Get archived threads (limited to avoid timeout)
                            async for thread in channel.archived_threads(limit=50):
                                threads.append(thread)
                            
                            # Add active threads
                            for thread in channel.threads:
                                threads.append(thread)
                            
                            for thread in threads:
                                try:
                                    # Check thread permissions
                                    thread_permissions = thread.permissions_for(guild.me)
                                    if not thread_permissions.read_message_history:
                                        continue
                                    
                                    thread_message_count = 0
                                    async for message in thread.history(limit=500, after=month_start_utc):
                                        thread_message_count += 1
                                        total_messages_scanned += 1
                                        
                                        if message.author.bot:
                                            continue
                                        
                                        # Try to match message author to student
                                        student = None
                                        if message.author.id in student_lookup:
                                            student = student_lookup[message.author.id]
                                        elif str(message.author).lower() in student_lookup:
                                            student = student_lookup[str(message.author).lower()]
                                        elif message.author.name.lower() in student_lookup:
                                            student = student_lookup[message.author.name.lower()]
                                        
                                        if student:
                                            activity = student_activity[student.discord_handle]
                                            
                                            # Count total messages (last 30 days)
                                            activity['total'] += 1
                                            
                                            # Count messages from last week
                                            if message.created_at >= week_start_utc:
                                                activity['week'] += 1
                                            
                                            # Track most recent message
                                            if not activity['last_message'] or message.created_at > activity['last_message']:
                                                activity['last_message'] = message.created_at
                                        
                                        # Rate limiting for threads too
                                        if thread_message_count % 25 == 0:
                                            await asyncio.sleep(0.1)
                                            
                                except discord.HTTPException as e:
                                    # Skip threads we can't access
                                    if progress_callback:
                                        await progress_callback(f"⚠️ Couldn't scan thread in {channel.name}: {str(e)[:50]}")
                                    continue
                        except discord.HTTPException as e:
                            if progress_callback:
                                await progress_callback(f"⚠️ Couldn't get threads for {channel.name}: {str(e)[:50]}")
                                
                except discord.HTTPException as e:
                    if progress_callback:
                        await progress_callback(f"⚠️ Couldn't scan {channel.name}: {str(e)[:50]}")
                    self.logger.error("health_check_channel_scan_failed",
                                    channel_name=channel.name,
                                    error=str(e))
                    continue
                except Exception as e:
                    if progress_callback:
                        await progress_callback(f"❌ Error scanning {channel.name}: {str(e)[:50]}")
                    self.logger.error("health_check_unexpected_error",
                                    channel_name=channel.name,
                                    error=str(e),
                                    error_type=type(e).__name__)
                    continue
            
            # Get member join dates
            if progress_callback:
                await progress_callback("📋 Collecting member information...")
            
            for student in students:
                if student.discord_id:
                    try:
                        member = guild.get_member(student.discord_id)
                        if member:
                            student_activity[student.discord_handle]['joined'] = member.joined_at
                    except Exception as e:
                        self.logger.error("health_check_member_info_failed",
                                        student_name=student.name,
                                        error=str(e))
            
            # Create StudentActivity objects
            activities = []
            for handle, data in student_activity.items():
                activity = StudentActivity(
                    student=data['student'],
                    total_messages=data['total'],
                    messages_last_week=data['week'],
                    last_message_date=data['last_message'],
                    member_since=data.get('joined')
                )
                activities.append(activity)
            
            # Sort by activity tier (At Risk first), then by total messages
            activities.sort(key=lambda x: (
                0 if x.activity_tier == "At Risk" else 1 if x.activity_tier == "Low Activity" else 2,
                x.total_messages
            ))
            
            if progress_callback:
                await progress_callback(f"✅ Scan complete: {total_messages_scanned} messages analyzed")
            
            self.logger.info("health_check_completed",
                            course_name=course_name,
                            students_checked=len(activities),
                            channels_scanned=len(channels),
                            total_messages_scanned=total_messages_scanned)
            
            return True, f"Health check completed for {len(activities)} students", activities
            
        except Exception as e:
            self.logger.error("health_check_critical_error",
                            course_name=course_name,
                            error=str(e),
                            error_type=type(e).__name__)
            return False, f"Health check failed: {str(e)}", []
    
    def debug_courses(self) -> Dict[str, Any]:
        """Get debug information about stored courses."""
        return {
            "total_courses": len(self._courses),
            "course_keys": list(self._courses.keys()),
            "course_details": {
                key: {
                    "display_name": config.name,
                    "role_id": config.role_id,
                    "category_id": config.category_id
                }
                for key, config in self._courses.items()
            }
        }