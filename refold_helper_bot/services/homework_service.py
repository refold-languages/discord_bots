"""
Homework service for Refold Helper Bot.
Handles automated homework posting and scheduling.
"""

import csv
import asyncio
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from io import StringIO

import discord

from .base_service import BaseService
from core import DataManager
from utils import get_logger, performance_monitor, safe_execute, ValidationError, DataError

@dataclass
class HomeworkAssignment:
    homework_id: str
    course_name: str
    title: str
    content: str
    scheduled_datetime: datetime
    course_day: int
    status: str = "pending"  # pending, posted, failed
    posted_at: Optional[datetime] = None
    error_message: Optional[str] = None
    forum_channel_id: Optional[int] = None
    thread_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['scheduled_datetime'] = self.scheduled_datetime.isoformat()
        if self.posted_at:
            data['posted_at'] = self.posted_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HomeworkAssignment':
        """Create from dictionary from JSON storage."""
        # Convert ISO strings back to datetime objects
        data['scheduled_datetime'] = datetime.fromisoformat(data['scheduled_datetime'])
        if data.get('posted_at'):
            data['posted_at'] = datetime.fromisoformat(data['posted_at'])
        return cls(**data)


class HomeworkService(BaseService):
    """Service for managing automated homework posting."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.homework')
        self.data_manager = DataManager()
        self._assignments: Dict[str, HomeworkAssignment] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    def initialize(self) -> None:
        super().initialize()
        self.logger.info("homework_service_initializing")
        self._load_homework_assignments()
    
    def _get_utc_now(self) -> datetime:
        """Get current UTC time as timezone-aware datetime."""
        return datetime.now(pytz.UTC)
    
    def _load_homework_assignments(self) -> None:
        """Load homework assignments from data manager."""
        try:
            data, _ = self.data_manager.load_data("homework_assignments")
            self._assignments = {}
            
            for assignment_id, assignment_data in data.get("assignments", {}).items():
                try:
                    self._assignments[assignment_id] = HomeworkAssignment.from_dict(assignment_data)
                except Exception as e:
                    self.logger.warning("invalid_homework_assignment_skipped",
                                      assignment_id=assignment_id,
                                      error=str(e))
            
            self.logger.info("homework_assignments_loaded",
                           assignment_count=len(self._assignments))
        except Exception as e:
            self.logger.error("homework_assignments_load_failed", error=str(e))
            self._assignments = {}
    
    @safe_execute("save_homework_assignments")
    async def _save_homework_assignments(self) -> bool:
        """Save homework assignments to data manager."""
        data, _ = self.data_manager.load_data("homework_assignments")
        
        # Update assignments data
        data["assignments"] = {
            assignment_id: assignment.to_dict()
            for assignment_id, assignment in self._assignments.items()
        }
        data["metadata"]["total_assignments"] = len(self._assignments)
        
        success, error = self.data_manager.save_data("homework_assignments", data)
        if not success:
            raise DataError(f"Failed to save homework assignments: {error}")
        
        return True
    
    def _generate_assignment_id(self, course_name: str, title: str, scheduled_datetime: datetime) -> str:
        """Generate unique assignment ID."""
        timestamp = scheduled_datetime.strftime("%Y%m%d_%H%M")
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_title = clean_title.replace(' ', '_')[:20]  # Limit length
        return f"{course_name.lower()}_{clean_title}_{timestamp}"
    
    @safe_execute("upload_homework_schedule")
    async def upload_homework_schedule(self, course_name: str, csv_content: str, forum_channel_id: int) -> Tuple[bool, str, List[str]]:
        """
        Upload homework schedule from CSV content.
        
        Args:
            course_name: Name of the course
            csv_content: CSV content with homework schedule
            forum_channel_id: Discord forum channel ID to post in
            
        Returns:
            Tuple of (success, message, warnings)
        """
        try:
            warnings = []
            new_assignments = []
            
            lines = csv_content.strip().split('\n')
            reader = csv.DictReader(lines)
            
            required_columns = {'title', 'text', 'post_date', 'post_time', 'course_day'}
            if not required_columns.issubset(reader.fieldnames):
                missing = required_columns - set(reader.fieldnames)
                return False, f"Missing required columns: {missing}", []
            
            pacific = pytz.timezone('US/Pacific')
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Validate required fields
                    title = row.get('title', '').strip()
                    text = row.get('text', '').strip()
                    text = text.replace('\\n', '\n')
                    post_date = row.get('post_date', '').strip()
                    post_time = row.get('post_time', '').strip()
                    course_day_str = row.get('course_day', '').strip()
                    
                    if not all([title, text, post_date, post_time, course_day_str]):
                        warnings.append(f"Row {row_num}: Missing required fields, skipping")
                        continue
                    
                    # Parse course day
                    try:
                        course_day = int(course_day_str)
                    except ValueError:
                        warnings.append(f"Row {row_num}: Invalid course day '{course_day_str}', skipping")
                        continue
                    
                    # Parse date and time
                    try:
                        # Parse date (YYYY-MM-DD)
                        date_parts = post_date.split('-')
                        if len(date_parts) != 3:
                            raise ValueError("Date must be in YYYY-MM-DD format")
                        
                        year, month, day = map(int, date_parts)
                        
                        # Parse time (HH:MM in 24hr format)
                        time_parts = post_time.split(':')
                        if len(time_parts) != 2:
                            raise ValueError("Time must be in HH:MM format")
                        
                        hour, minute = map(int, time_parts)
                        
                        # Create datetime in Pacific timezone
                        scheduled_dt = pacific.localize(datetime(year, month, day, hour, minute))
                        
                        # Convert to UTC for storage
                        scheduled_dt_utc = scheduled_dt.astimezone(pytz.UTC)
                        
                    except ValueError as e:
                        warnings.append(f"Row {row_num}: Invalid date/time - {str(e)}, skipping")
                        continue
                    
                    # Check if assignment already exists
                    assignment_id = self._generate_assignment_id(course_name, title, scheduled_dt_utc)
                    if assignment_id in self._assignments:
                        warnings.append(f"Row {row_num}: Assignment '{title}' already exists, skipping")
                        continue
                    
                    # Create assignment
                    assignment = HomeworkAssignment(
                        homework_id=assignment_id,
                        course_name=course_name,
                        title=title,
                        content=text,
                        scheduled_datetime=scheduled_dt_utc,
                        course_day=course_day,
                        forum_channel_id=forum_channel_id
                    )
                    
                    new_assignments.append(assignment)
                    
                except Exception as e:
                    warnings.append(f"Row {row_num}: Error processing - {str(e)}, skipping")
                    continue
            
            if not new_assignments:
                return False, "No valid homework assignments found in CSV", warnings
            
            # Add all new assignments
            for assignment in new_assignments:
                self._assignments[assignment.homework_id] = assignment
            
            # Save to storage
            await self._save_homework_assignments()
            
            self.logger.info("homework_schedule_uploaded",
                           course_name=course_name,
                           assignments_added=len(new_assignments),
                           warnings_count=len(warnings))
            
            return True, f"Successfully uploaded {len(new_assignments)} homework assignments", warnings
            
        except Exception as e:
            self.logger.error("homework_upload_failed",
                            course_name=course_name,
                            error=str(e))
            return False, f"Upload failed: {str(e)}", []
    
    def get_pending_assignments(self, course_name: str = None) -> List[HomeworkAssignment]:
        """Get pending assignments, optionally filtered by course."""
        assignments = [
            a for a in self._assignments.values()
            if a.status == "pending"
        ]
        
        if course_name:
            assignments = [a for a in assignments if a.course_name.lower() == course_name.lower()]
        
        # Sort by scheduled time
        assignments.sort(key=lambda x: x.scheduled_datetime)
        return assignments
    
    def get_all_assignments(self, course_name: str = None) -> List[HomeworkAssignment]:
        """Get all assignments, optionally filtered by course."""
        assignments = list(self._assignments.values())
        
        if course_name:
            assignments = [a for a in assignments if a.course_name.lower() == course_name.lower()]
        
        # Sort by scheduled time
        assignments.sort(key=lambda x: x.scheduled_datetime)
        return assignments
    
    @safe_execute("cancel_assignment")
    async def cancel_assignment(self, assignment_id: str) -> Tuple[bool, str]:
        """Cancel a homework assignment."""
        if assignment_id not in self._assignments:
            return False, f"Assignment '{assignment_id}' not found"
        
        assignment = self._assignments[assignment_id]
        if assignment.status != "pending":
            return False, f"Assignment '{assignment_id}' is already {assignment.status}"
        
        # Remove from memory
        del self._assignments[assignment_id]
        
        # Save changes
        await self._save_homework_assignments()
        
        self.logger.info("homework_assignment_cancelled",
                        assignment_id=assignment_id,
                        title=assignment.title)
        
        return True, f"Assignment '{assignment.title}' cancelled"
    
    @safe_execute("mark_assignment_posted")
    async def mark_assignment_posted(self, assignment_id: str, thread_id: int) -> bool:
        """Mark assignment as successfully posted."""
        if assignment_id in self._assignments:
            assignment = self._assignments[assignment_id]
            assignment.status = "posted"
            assignment.posted_at = self._get_utc_now()
            assignment.thread_id = thread_id
            assignment.error_message = None
            
            await self._save_homework_assignments()
            
            self.logger.info("homework_assignment_posted",
                           assignment_id=assignment_id,
                           thread_id=thread_id)
            return True
        return False
    
    @safe_execute("mark_assignment_failed")
    async def mark_assignment_failed(self, assignment_id: str, error_message: str) -> bool:
        """Mark assignment as failed to post."""
        if assignment_id in self._assignments:
            assignment = self._assignments[assignment_id]
            assignment.status = "failed"
            assignment.error_message = error_message
            
            await self._save_homework_assignments()
            
            self.logger.error("homework_assignment_failed",
                            assignment_id=assignment_id,
                            error=error_message)
            return True
        return False
    
    def get_upcoming_assignments(self, hours_ahead: int = 24) -> List[HomeworkAssignment]:
        """Get assignments scheduled within the next N hours."""
        cutoff = self._get_utc_now() + timedelta(hours=hours_ahead)
        
        upcoming = [
            a for a in self._assignments.values()
            if a.status == "pending" and a.scheduled_datetime <= cutoff
        ]
        
        upcoming.sort(key=lambda x: x.scheduled_datetime)
        return upcoming
    
    def get_overdue_assignments(self) -> List[HomeworkAssignment]:
        """Get assignments that should have been posted but are still pending."""
        now = self._get_utc_now()
        
        overdue = [
            a for a in self._assignments.values()
            if a.status == "pending" and a.scheduled_datetime <= now
        ]
        
        overdue.sort(key=lambda x: x.scheduled_datetime)
        return overdue
    
    def start_scheduler(self, bot) -> None:
        """Start the homework posting scheduler."""
        if self._scheduler_task and not self._scheduler_task.done():
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop(bot))
        self.logger.info("homework_scheduler_started")
    
    def stop_scheduler(self) -> None:
        """Stop the homework posting scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
        self.logger.info("homework_scheduler_stopped")
    
    async def _scheduler_loop(self, bot) -> None:
        """Main scheduler loop that posts homework assignments."""
        while self._running:
            try:
                now = self._get_utc_now()
                self.logger.debug("homework_scheduler_check", 
                                current_time=now.isoformat(),
                                total_assignments=len(self._assignments))
                
                # Find assignments that need to be posted
                due_assignments = [
                    a for a in self._assignments.values()
                    if a.status == "pending" and a.scheduled_datetime <= now
                ]
                
                if due_assignments:
                    self.logger.info("homework_assignments_due", 
                                   count=len(due_assignments),
                                   assignments=[a.title for a in due_assignments])
                
                for assignment in due_assignments:
                    try:
                        self.logger.info("attempting_homework_post",
                                       assignment_id=assignment.homework_id,
                                       title=assignment.title,
                                       scheduled_time=assignment.scheduled_datetime.isoformat())
                        
                        await self._post_homework_assignment(bot, assignment)
                        
                    except Exception as e:
                        error_msg = str(e)
                        self.logger.error("homework_post_failed",
                                        assignment_id=assignment.homework_id,
                                        title=assignment.title,
                                        error=error_msg,
                                        error_type=type(e).__name__)
                        
                        await self.mark_assignment_failed(assignment.homework_id, error_msg)
                
                # Sleep for 60 seconds before checking again
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                self.logger.info("homework_scheduler_cancelled")
                break
            except Exception as e:
                self.logger.error("homework_scheduler_error", 
                                error=str(e),
                                error_type=type(e).__name__)
                await asyncio.sleep(60)  # Continue after error
    
    async def _post_homework_assignment(self, bot, assignment: HomeworkAssignment) -> None:
        """Post a homework assignment to Discord."""
        try:
            # Get the forum channel
            channel = bot.get_channel(assignment.forum_channel_id)
            if not channel:
                raise Exception(f"Forum channel {assignment.forum_channel_id} not found")
            
            if not isinstance(channel, discord.ForumChannel):
                raise Exception(f"Channel {assignment.forum_channel_id} is not a forum channel")
            
            # Check permissions
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.create_public_threads:
                raise Exception(f"Missing permission to create threads in {channel.name}")
            
            if not permissions.send_messages:
                raise Exception(f"Missing permission to send messages in {channel.name}")
            
            self.logger.info("posting_homework_to_forum",
                           assignment_id=assignment.homework_id,
                           channel_name=channel.name,
                           channel_id=assignment.forum_channel_id)
            
            # Create the forum post with thread
            thread, message = await channel.create_thread(
                name=assignment.title,
                content=assignment.content
            )
            
            # Mark as posted
            await self.mark_assignment_posted(assignment.homework_id, thread.id)
            
            self.logger.info("homework_posted_successfully",
                           assignment_id=assignment.homework_id,
                           title=assignment.title,
                           thread_id=thread.id,
                           channel_id=assignment.forum_channel_id,
                           channel_name=channel.name)
            
        except discord.Forbidden as e:
            raise Exception(f"Permission denied to post in forum: {str(e)}")
        except discord.HTTPException as e:
            raise Exception(f"Discord API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to post homework: {str(e)}")
    
    def get_schedule_summary(self) -> Dict[str, Any]:
        """Get summary of homework schedule."""
        all_assignments = list(self._assignments.values())
        
        by_status = {}
        by_course = {}
        
        for assignment in all_assignments:
            # Count by status
            by_status[assignment.status] = by_status.get(assignment.status, 0) + 1
            
            # Count by course
            by_course[assignment.course_name] = by_course.get(assignment.course_name, 0) + 1
        
        pending = self.get_pending_assignments()
        overdue = self.get_overdue_assignments()
        
        return {
            "total_assignments": len(all_assignments),
            "by_status": by_status,
            "by_course": by_course,
            "pending_count": len(pending),
            "overdue_count": len(overdue),
            "next_assignment": pending[0].scheduled_datetime.isoformat() if pending else None,
            "scheduler_running": self._running
        }