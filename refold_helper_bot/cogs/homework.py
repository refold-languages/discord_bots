"""
Homework cog for Refold Helper Bot.
Handles automated homework posting and scheduling.
"""

import discord
from discord.ext import commands
from typing import Optional

from services import HomeworkService, CourseService
from utils import get_logger, monitor_command, ValidationError, DiscordError

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
    
    def cog_check(self, ctx):
        """Global check - only works in allowed course servers."""
        return (ctx.guild and 
                self.course_service.is_course_server(ctx.guild.id))
    
    async def cog_command_error(self, ctx, error):
        """Handle homework cog specific errors."""
        if isinstance(error, commands.CheckFailure):
            # Don't send any message - we want these commands to be invisible to other servers
            return
        
        # Let the global error handler deal with other errors
        raise error
    
    @commands.group(name='homework', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def homework_group(self, ctx):
        """Homework management commands."""
        await ctx.send("Use `!homework upload`, `!homework status`, `!homework list`, or `!homework cancel`")
    
    @homework_group.command(name='upload')
    @monitor_command()
    async def upload_homework(self, ctx, course_name: str, forum_channel_id: int, *, csv_content: str = None):
        """Upload homework schedule from CSV content.
        
        Usage: !homework upload "Course Name" 1234567890123456789
        Then paste CSV content in next message, or include after command.
        
        CSV Format: title,text,post_date,post_time,course_day
        Example:
        title,text,post_date,post_time,course_day
        "Week 1 Homework","Complete exercises 1-5\\n\\n**Due:** Friday 11:59 PM","2025-08-15","09:00","1"
        """
        # Check if this is a backend channel
        if not self.course_service.is_backend_channel(ctx.channel.id):
            await ctx.send("❌ Homework uploads are only allowed in backend channels.")
            return
        
        # Verify course exists
        course = self.course_service.get_course(course_name)
        if not course:
            await ctx.send(f"❌ Course '{course_name}' not found. Use `!course add` to create it first.")
            return
        
        # Get and validate forum channel
        try:
            forum_channel = self.bot.get_channel(forum_channel_id)
            if not forum_channel:
                await ctx.send(f"❌ Channel with ID {forum_channel_id} not found.")
                return
            
            if not isinstance(forum_channel, discord.ForumChannel):
                await ctx.send(f"❌ Channel {forum_channel.name} (ID: {forum_channel_id}) is not a forum channel.")
                return
            
            # Check if bot has permissions
            permissions = forum_channel.permissions_for(ctx.guild.me)
            if not (permissions.create_public_threads and permissions.send_messages):
                await ctx.send(f"❌ I don't have permission to create threads in {forum_channel.name}.")
                return
            
        except Exception as e:
            await ctx.send(f"❌ Error accessing channel {forum_channel_id}: {str(e)}")
            return
        
        # Get CSV content if not provided
        if not csv_content:
            await ctx.send("📋 Please paste your CSV content (you have 60 seconds):")
            
            def check(message):
                return (message.author == ctx.author and 
                       message.channel == ctx.channel)
            
            try:
                csv_message = await self.bot.wait_for('message', timeout=60.0, check=check)
                csv_content = csv_message.content
            except:
                await ctx.send("⏰ Timed out waiting for CSV content.")
                return
        
        # Clean up CSV content
        csv_content = csv_content.strip()
        if csv_content.startswith('```'):
            csv_content = '\n'.join(csv_content.split('\n')[1:-1])
        
        # Upload the schedule
        progress_msg = await ctx.send("⏳ Processing homework schedule...")
        
        success, message, warnings = await self.homework_service.upload_homework_schedule(
            course_name, csv_content, forum_channel_id
        )
        
        if success:
            embed = discord.Embed(title="✅ Homework Schedule Uploaded", color=0x00ff00)
            embed.add_field(name="Result", value=message, inline=False)
            embed.add_field(name="Course", value=course_name, inline=True)
            embed.add_field(name="Forum Channel", value=f"{forum_channel.name} (ID: {forum_channel_id})", inline=True)
            
            if warnings:
                embed.add_field(
                    name="⚠️ Warnings",
                    value="\n".join(warnings[:5]),  # Limit to first 5
                    inline=False
                )
                if len(warnings) > 5:
                    embed.add_field(name="...", value=f"and {len(warnings) - 5} more warnings", inline=False)
            
            await progress_msg.edit(content="", embed=embed)
        else:
            embed = discord.Embed(title="❌ Upload Failed", color=0xff0000)
            embed.add_field(name="Error", value=message, inline=False)
            
            if warnings:
                embed.add_field(
                    name="Issues Found",
                    value="\n".join(warnings[:10]),
                    inline=False
                )
            
            await progress_msg.edit(content="", embed=embed)
    
    @homework_group.command(name='status')
    @monitor_command()
    async def homework_status(self, ctx, course_name: str = None):
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
            import pytz
            
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
        
        await ctx.send(embed=embed)
    
    @homework_group.command(name='list')
    @monitor_command()
    async def list_homework(self, ctx, course_name: str = None, status: str = "pending"):
        """List homework assignments.
        
        Usage: !homework list [course_name] [status]
        Status can be: pending, posted, failed, all
        """
        if status not in ["pending", "posted", "failed", "all"]:
            await ctx.send("❌ Status must be one of: pending, posted, failed, all")
            return
        
        if status == "all":
            assignments = self.homework_service.get_all_assignments(course_name)
        else:
            assignments = [
                a for a in self.homework_service.get_all_assignments(course_name)
                if a.status == status
            ]
        
        if not assignments:
            course_filter = f" for {course_name}" if course_name else ""
            await ctx.send(f"📋 No {status} assignments found{course_filter}.")
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
            import pytz
            pacific = pytz.timezone('US/Pacific')
            scheduled_pacific = assignment.scheduled_datetime.astimezone(pacific)
            
            value = f"**Course:** {assignment.course_name}\n"
            value += f"**Day:** {assignment.course_day}\n"
            value += f"**Scheduled:** {scheduled_pacific.strftime('%Y-%m-%d %I:%M %p PT')}\n"
            value += f"**Status:** {assignment.status}"
            
            if assignment.status == "posted" and assignment.thread_id:
                value += f"\n**Thread:** [View](<https://discord.com/channels/{ctx.guild.id}/{assignment.thread_id}>)"
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
        
        await ctx.send(embed=embed)
    
    @homework_group.command(name='cancel')
    @monitor_command()
    async def cancel_homework(self, ctx, *, assignment_title: str):
        """Cancel a pending homework assignment by title.
        
        Usage: !homework cancel "Assignment Title"
        """
        # Find assignment by title
        pending = self.homework_service.get_pending_assignments()
        matching = [a for a in pending if assignment_title.lower() in a.title.lower()]
        
        if not matching:
            await ctx.send(f"❌ No pending assignment found matching '{assignment_title}'")
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
            await ctx.send(embed=embed)
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
        
        import pytz
        pacific = pytz.timezone('US/Pacific')
        scheduled_pacific = assignment.scheduled_datetime.astimezone(pacific)
        embed.add_field(
            name="Scheduled",
            value=scheduled_pacific.strftime('%Y-%m-%d %I:%M %p PT'),
            inline=True
        )
        
        embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, user):
            return (user == ctx.author and 
                    str(reaction.emoji) in ["✅", "❌"] and 
                    reaction.message.id == message.id)
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                success, result_message = await self.homework_service.cancel_assignment(assignment.homework_id)
                
                if success:
                    await ctx.send(f"✅ {result_message}")
                else:
                    await ctx.send(f"❌ {result_message}")
            else:
                await ctx.send("❌ Cancellation cancelled.")
                
        except:
            await ctx.send("⏰ Cancellation timed out. No changes made.")
        
        # Clean up the confirmation message
        try:
            await message.delete()
        except discord.NotFound:
            pass
    
    @homework_group.command(name='preview')
    @monitor_command()
    async def preview_homework(self, ctx, *, assignment_title: str):
        """Preview what a homework assignment will look like when posted.
        
        Usage: !homework preview "Assignment Title"
        """
        # Find assignment by title
        pending = self.homework_service.get_pending_assignments()
        matching = [a for a in pending if assignment_title.lower() in a.title.lower()]
        
        if not matching:
            await ctx.send(f"❌ No pending assignment found matching '{assignment_title}'")
            return
        
        if len(matching) > 1:
            await ctx.send(f"❌ Multiple assignments found. Please be more specific.")
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
        import pytz
        pacific = pytz.timezone('US/Pacific')
        scheduled_pacific = assignment.scheduled_datetime.astimezone(pacific)
        
        embed.add_field(name="Scheduled Time", 
                       value=scheduled_pacific.strftime('%Y-%m-%d %I:%M %p PT'), 
                       inline=True)
        embed.add_field(name="Course", value=assignment.course_name, inline=True)
        embed.add_field(name="Course Day", value=str(assignment.course_day), inline=True)
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Add the Homework cog to the bot."""
    await bot.add_cog(Homework(bot))