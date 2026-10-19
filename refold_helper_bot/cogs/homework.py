"""
Homework cog for Refold Helper Bot.
Handles automated homework posting and scheduling.
"""

from typing import List, Optional

import discord
import pytz
from discord import app_commands
from discord.ext import commands

from services import HomeworkService, CourseService
from utils import get_logger, monitor_command, ValidationError, DiscordError
from utils.interactions import respond, confirm, read_text_attachment

class Homework(commands.Cog):
    """Homework scheduling and automation for courses."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.homework')
        self.homework_service = HomeworkService()
        self.course_service = CourseService()
    
    async def cog_load(self):
        """Initialize services when cog loads."""
        self.homework_service.initialize()
        self.course_service.initialize()
        
        # Start the homework scheduler
        self.homework_service.start_scheduler(self.bot)
        self.logger.info("homework_cog_loaded")
    
    def cog_unload(self):
        """Clean up when cog unloads."""
        self.homework_service.stop_scheduler()
        self.logger.info("homework_cog_unloaded")
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Homework commands only work in the allowed course servers."""
        if interaction.guild_id is None or not self.course_service.is_course_server(interaction.guild_id):
            raise app_commands.CheckFailure("Homework commands are not enabled in this server.")
        return True

    homework_group = app_commands.Group(
        name='homework', description='Scheduled homework posts',
        default_permissions=discord.Permissions(administrator=True), guild_only=True)

    @homework_group.command(name='upload', description='Upload a homework schedule from a CSV file')
    @app_commands.describe(course_name='Course the homework belongs to',
                           forum='Forum channel to post the homework in',
                           file='CSV with columns: title,text,post_date,post_time,course_day')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def upload_homework(self, interaction: discord.Interaction, course_name: str,
                              forum: discord.ForumChannel, file: discord.Attachment):
        """Upload homework schedule from an uploaded CSV file.
        
        CSV Format: title,text,post_date,post_time,course_day
        Example:
        title,text,post_date,post_time,course_day
        "Week 1 Homework","Complete exercises 1-5\\n\\n**Due:** Friday 11:59 PM","2025-08-15","09:00","1"
        """
        # Check if this is a backend channel
        if not self.course_service.is_backend_channel(interaction.channel_id):
            await interaction.response.send_message("❌ Homework uploads are only allowed in backend channels.",
                                                    ephemeral=True)
            return
        
        # Verify course exists
        course = self.course_service.get_course(course_name)
        if not course:
            await interaction.response.send_message(
                f"❌ Course '{course_name}' not found. Use `/course add` to create it first.", ephemeral=True)
            return
        
        # Check if bot has permissions
        permissions = forum.permissions_for(interaction.guild.me)
        if not (permissions.create_public_threads and permissions.send_messages):
            await interaction.response.send_message(
                f"❌ I don't have permission to create threads in {forum.name}.", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        try:
            csv_content = (await read_text_attachment(file)).strip()
        except ValueError as e:
            await respond(interaction, f"❌ {e}")
            return
        
        success, message, warnings = await self.homework_service.upload_homework_schedule(
            course_name, csv_content, forum.id
        )
        
        if success:
            embed = discord.Embed(title="✅ Homework Schedule Uploaded", color=0x00ff00)
            embed.add_field(name="Result", value=message, inline=False)
            embed.add_field(name="Course", value=course_name, inline=True)
            embed.add_field(name="Forum Channel", value=f"{forum.name} (ID: {forum.id})", inline=True)
            
            if warnings:
                embed.add_field(
                    name="⚠️ Warnings",
                    value="\n".join(warnings[:5])[:1024],  # Limit to first 5
                    inline=False
                )
                if len(warnings) > 5:
                    embed.add_field(name="...", value=f"and {len(warnings) - 5} more warnings", inline=False)
        else:
            embed = discord.Embed(title="❌ Upload Failed", color=0xff0000)
            embed.add_field(name="Error", value=message[:1024], inline=False)
            
            if warnings:
                embed.add_field(
                    name="Issues Found",
                    value="\n".join(warnings[:10])[:1024],
                    inline=False
                )
        
        await respond(interaction, embed=embed)
    
    @homework_group.command(name='status', description='Show homework scheduling status')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def homework_status(self, interaction: discord.Interaction):
        """Show homework scheduling status."""
        summary = self.homework_service.get_schedule_summary()
        
        embed = discord.Embed(title="📚 Homework Schedule Status", color=0x0099ff)
        
        # Overall stats
        embed.add_field(name="Total Assignments", value=str(summary['total_assignments']), inline=True)
        embed.add_field(name="Pending", value=str(summary['pending_count']), inline=True)
        embed.add_field(name="Overdue", value=str(summary['overdue_count']), inline=True)
        
        # Scheduler status
        scheduler_status = "🟢 Running" if summary['scheduler_running'] else "🔴 Stopped"
        embed.add_field(name="Scheduler", value=scheduler_status, inline=True)
        
        # Next assignment
        if summary['next_assignment']:
            from datetime import datetime
            
            next_dt = datetime.fromisoformat(summary['next_assignment'])
            pacific = pytz.timezone('US/Pacific')
            next_pacific = next_dt.astimezone(pacific)
            
            embed.add_field(
                name="Next Assignment",
                value=f"<t:{int(next_dt.timestamp())}:R>\n{next_pacific.strftime('%Y-%m-%d %I:%M %p PT')}",
                inline=True
            )
        
        # Status breakdown
        status_text = []
        for status, count in summary['by_status'].items():
            status_text.append(f"{status}: {count}")
        if status_text:
            embed.add_field(name="By Status", value="\n".join(status_text), inline=True)
        
        # Course breakdown (if multiple courses)
        if len(summary['by_course']) > 1:
            course_text = []
            for course, count in summary['by_course'].items():
                course_text.append(f"{course}: {count}")
            embed.add_field(name="By Course", value="\n".join(course_text), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @homework_group.command(name='list', description='List homework assignments')
    @app_commands.describe(course_name='Only this course (default: all)', status='Which assignments to show')
    @app_commands.choices(status=[app_commands.Choice(name=s, value=s)
                                  for s in ("pending", "posted", "failed", "all")])
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def list_homework(self, interaction: discord.Interaction, course_name: Optional[str] = None,
                            status: str = "pending"):
        """List homework assignments."""

        if status == "all":
            assignments = self.homework_service.get_all_assignments(course_name)
        else:
            assignments = [
                a for a in self.homework_service.get_all_assignments(course_name)
                if a.status == status
            ]
        
        if not assignments:
            course_filter = f" for {course_name}" if course_name else ""
            await interaction.response.send_message(f"📋 No {status} assignments found{course_filter}.",
                                                    ephemeral=True)
            return
        
        # Create paginated embed
        embed = discord.Embed(
            title=f"📚 Homework Assignments ({status.title()})",
            color=0x0099ff
        )
        
        if course_name:
            embed.add_field(name="Course", value=course_name, inline=True)
        
        # Show up to 10 assignments
        display_assignments = assignments[:10]
        
        for assignment in display_assignments:
            # Format time
            pacific = pytz.timezone('US/Pacific')
            scheduled_pacific = assignment.scheduled_datetime.astimezone(pacific)
            
            value = f"**Course:** {assignment.course_name}\n"
            value += f"**Day:** {assignment.course_day}\n"
            value += f"**Scheduled:** {scheduled_pacific.strftime('%Y-%m-%d %I:%M %p PT')}\n"
            value += f"**Status:** {assignment.status}"
            
            if assignment.status == "posted" and assignment.thread_id:
                value += f"\n**Thread:** [View](<https://discord.com/channels/{interaction.guild_id}/{assignment.thread_id}>)"
            elif assignment.status == "failed" and assignment.error_message:
                value += f"\n**Error:** {assignment.error_message[:100]}"
            
            embed.add_field(
                name=f"{assignment.title}",
                value=value,
                inline=False
            )
        
        if len(assignments) > 10:
            embed.add_field(
                name="...",
                value=f"and {len(assignments) - 10} more assignments",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @homework_group.command(name='cancel', description='Cancel a pending homework assignment')
    @app_commands.describe(assignment_title='Title (or part of it) of the pending assignment')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def cancel_homework(self, interaction: discord.Interaction, assignment_title: str):
        """Cancel a pending homework assignment by title."""
        # Find assignment by title
        pending = self.homework_service.get_pending_assignments()
        matching = [a for a in pending if assignment_title.lower() in a.title.lower()]
        
        if not matching:
            await interaction.response.send_message(
                f"❌ No pending assignment found matching '{assignment_title}'", ephemeral=True)
            return
        
        if len(matching) > 1:
            # Multiple matches, show options
            embed = discord.Embed(title="Multiple Assignments Found", color=0xff9900)
            for i, assignment in enumerate(matching[:5], 1):
                embed.add_field(
                    name=f"{i}. {assignment.title}",
                    value=f"Course: {assignment.course_name}\nDay: {assignment.course_day}",
                    inline=False
                )
            embed.add_field(
                name="Instructions",
                value="Please be more specific with the assignment title.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        assignment = matching[0]
        
        # Confirm cancellation
        embed = discord.Embed(
            title="⚠️ Confirm Cancellation",
            description=f"Are you sure you want to cancel this assignment?",
            color=0xff9900
        )
        embed.add_field(name="Title", value=assignment.title, inline=False)
        embed.add_field(name="Course", value=assignment.course_name, inline=True)
        embed.add_field(name="Day", value=str(assignment.course_day), inline=True)
        
        pacific = pytz.timezone('US/Pacific')
        scheduled_pacific = assignment.scheduled_datetime.astimezone(pacific)
        embed.add_field(
            name="Scheduled",
            value=scheduled_pacific.strftime('%Y-%m-%d %I:%M %p PT'),
            inline=True
        )
        
        if not await confirm(interaction, None, embed=embed, timeout=30.0, confirm_label='Cancel assignment'):
            return

        success, result_message = await self.homework_service.cancel_assignment(assignment.homework_id)
        if success:
            await respond(interaction, f"✅ {result_message}", ephemeral=True)
        else:
            await respond(interaction, f"❌ {result_message}", ephemeral=True)
    
    @homework_group.command(name='preview', description='Preview a pending homework post')
    @app_commands.describe(assignment_title='Title (or part of it) of the pending assignment')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def preview_homework(self, interaction: discord.Interaction, assignment_title: str):
        """Preview what a homework assignment will look like when posted."""
        # Find assignment by title
        pending = self.homework_service.get_pending_assignments()
        matching = [a for a in pending if assignment_title.lower() in a.title.lower()]
        
        if not matching:
            await interaction.response.send_message(
                f"❌ No pending assignment found matching '{assignment_title}'", ephemeral=True)
            return
        
        if len(matching) > 1:
            await interaction.response.send_message(
                f"❌ Multiple assignments found. Please be more specific.", ephemeral=True)
            return
        
        assignment = matching[0]
        
        # Create preview embed
        embed = discord.Embed(
            title="📋 Homework Preview",
            description="This is how the assignment will appear when posted:",
            color=0x0099ff
        )
        
        # Show the actual content as it will appear
        embed.add_field(name="Forum Thread Title", value=assignment.title, inline=False)
        embed.add_field(name="Forum Post Content", value=assignment.content[:1000], inline=False)
        
        if len(assignment.content) > 1000:
            embed.add_field(name="...", value="(content truncated for preview)", inline=False)
        
        # Show scheduling info
        pacific = pytz.timezone('US/Pacific')
        scheduled_pacific = assignment.scheduled_datetime.astimezone(pacific)
        
        embed.add_field(name="Scheduled Time", 
                       value=scheduled_pacific.strftime('%Y-%m-%d %I:%M %p PT'), 
                       inline=True)
        embed.add_field(name="Course", value=assignment.course_name, inline=True)
        embed.add_field(name="Course Day", value=str(assignment.course_day), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @upload_homework.autocomplete('course_name')
    @list_homework.autocomplete('course_name')
    async def _course_autocomplete(self, interaction: discord.Interaction,
                                   current: str) -> List[app_commands.Choice[str]]:
        current = current.lower()
        names = [c.name for c in self.course_service.get_all_courses().values()
                 if current in c.name.lower()]
        return [app_commands.Choice(name=n[:100], value=n[:100]) for n in names[:25]]

    @cancel_homework.autocomplete('assignment_title')
    @preview_homework.autocomplete('assignment_title')
    async def _assignment_autocomplete(self, interaction: discord.Interaction,
                                       current: str) -> List[app_commands.Choice[str]]:
        current = current.lower()
        titles = [a.title for a in self.homework_service.get_pending_assignments()
                  if current in a.title.lower()]
        return [app_commands.Choice(name=t[:100], value=t[:100]) for t in titles[:25]]


async def setup(bot):
    """Add the Homework cog to the bot."""
    await bot.add_cog(Homework(bot))