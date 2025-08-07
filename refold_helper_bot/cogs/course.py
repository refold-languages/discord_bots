"""
Course management cog for Refold Helper Bot.
Handles course configuration and student management for the learning platform.
"""

import asyncio
import discord
from discord.ext import commands
from typing import Optional

from services import CourseService
from utils import get_logger, monitor_command, ValidationError, DiscordError

class Course(commands.Cog):
    """Course management for the Refold learning platform."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.course')
        self.course_service = CourseService()
    
    async def cog_load(self):
        """Initialize the course service when cog loads."""
        self.course_service.initialize()
        self.logger.info("course_cog_loaded")
    
    def cog_check(self, ctx):
        """Global check - only works in allowed course servers."""
        return (ctx.guild and 
                self.course_service.is_course_server(ctx.guild.id))
    
    async def cog_command_error(self, ctx, error):
        """Handle course cog specific errors."""
        if isinstance(error, commands.CheckFailure):
            # Don't send any message - we want these commands to be invisible to other servers
            return
        
        # Let the global error handler deal with other errors
        raise error
    
    # Debug command to check which server you're on
    @commands.command(name='coursetest', hidden=True)
    @commands.has_permissions(administrator=True)
    async def course_test(self, ctx):
        """Test if course commands work in this server."""
        server_name = ctx.guild.name
        server_id = ctx.guild.id
        is_allowed = self.course_service.is_course_server(server_id)
        
        embed = discord.Embed(
            title="Course Feature Test",
            color=0x00ff00 if is_allowed else 0xff0000
        )
        embed.add_field(name="Server", value=server_name, inline=True)
        embed.add_field(name="Server ID", value=str(server_id), inline=True)
        embed.add_field(name="Course Features", value="✅ Enabled" if is_allowed else "❌ Disabled", inline=True)
        
        # Add debug info
        debug_info = self.course_service.debug_courses()
        embed.add_field(name="Debug Info", 
                       value=f"Courses: {debug_info['total_courses']}\nKeys: {debug_info['course_keys']}", 
                       inline=False)
        
        await ctx.send(embed=embed)
    
    # Course Configuration Commands
    @commands.group(name='course', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def course_group(self, ctx):
        """Course management commands."""
        await ctx.send("Use `!course list`, `!course add`, or `!course info <name>`")
    
    @course_group.command(name='add')
    @monitor_command()
    async def add_course(self, ctx, name: str, role_id: int, category_id: int):
        """Add a new course configuration.
        
        Example: !course add "Level Up Your Listening" 1234567890 9876543210
        """
        success, message = await self.course_service.add_course(name, role_id, category_id)
        
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")
    
    @course_group.command(name='remove')
    @monitor_command()
    async def remove_course(self, ctx, *, name: str):
        """Remove a course configuration.
        
        Example: !course remove "Test Course"
        """
        # First check if course exists
        course = self.course_service.get_course(name)
        if not course:
            available_courses = list(self.course_service.get_all_courses().keys())
            error_msg = f"❌ Course '{name}' not found."
            if available_courses:
                error_msg += f"\nAvailable courses: {', '.join(available_courses)}"
            await ctx.send(error_msg)
            return
        
        # Confirm removal
        embed = discord.Embed(
            title="⚠️ Confirm Course Removal",
            description=f"Are you sure you want to remove course **{course.name}**?",
            color=0xff9900
        )
        
        role = ctx.guild.get_role(course.role_id)
        category = ctx.guild.get_channel(course.category_id)
        
        embed.add_field(name="Role", value=role.mention if role else "Not found", inline=True)
        embed.add_field(name="Category", value=category.name if category else "Not found", inline=True)
        
        # Get channel count
        category_channels = self.course_service.get_category_channels(ctx.guild, course.category_id)
        embed.add_field(name="Channels", value=f"{len(category_channels)} channels", inline=True)
        
        embed.add_field(
            name="⚠️ Warning", 
            value="This will only remove the course from bot configuration.\nDiscord roles and channels will NOT be deleted.",
            inline=False
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
                # Remove the course
                success, result_message = await self.course_service.remove_course(name)
                
                if success:
                    await ctx.send(f"✅ {result_message}")
                else:
                    await ctx.send(f"❌ {result_message}")
            else:
                await ctx.send("❌ Course removal cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Course removal timed out. No changes made.")
        
        # Clean up the confirmation message
        try:
            await message.delete()
        except discord.NotFound:
            pass
    
    @course_group.command(name='list')
    @monitor_command()
    async def list_courses(self, ctx):
        """List all configured courses."""
        courses = self.course_service.get_all_courses()
        
        if not courses:
            await ctx.send("No courses configured yet.")
            return
        
        embed = discord.Embed(title="Configured Courses", color=0x00ff00)
        
        for course in courses.values():
            role = ctx.guild.get_role(course.role_id)
            category = ctx.guild.get_channel(course.category_id)
            
            # Get actual channels in the category
            category_channels = self.course_service.get_category_channels(ctx.guild, course.category_id)
            
            value = f"Role: {role.mention if role else 'Not found'}\n"
            value += f"Category: {category.name if category else 'Not found'}\n"
            value += f"Channels: {len(category_channels)} found"
            
            # Show channel breakdown if any exist
            if category_channels:
                text_count = len([c for c in category_channels if c['type'] == 'text'])
                voice_count = len([c for c in category_channels if c['type'] == 'voice'])
                other_count = len(category_channels) - text_count - voice_count
                
                breakdown = []
                if text_count > 0:
                    breakdown.append(f"{text_count} text")
                if voice_count > 0:
                    breakdown.append(f"{voice_count} voice")
                if other_count > 0:
                    breakdown.append(f"{other_count} other")
                
                if breakdown:
                    value += f" ({', '.join(breakdown)})"
            
            embed.add_field(name=course.name, value=value, inline=True)
        
        await ctx.send(embed=embed)
    
    @course_group.command(name='info')
    @monitor_command()
    async def course_info(self, ctx, *, name: str):
        """Get detailed info about a specific course."""
        course = self.course_service.get_course(name)
        
        if not course:
            # Add debug info to help troubleshoot
            debug_info = self.course_service.debug_courses()
            error_msg = f"❌ Course '{name}' not found.\n"
            error_msg += f"Available courses: {list(debug_info['course_keys'])}"
            await ctx.send(error_msg)
            return
        
        embed = discord.Embed(title=f"Course: {course.name}", color=0x0099ff)
        
        role = ctx.guild.get_role(course.role_id)
        category = ctx.guild.get_channel(course.category_id)
        
        embed.add_field(name="Role", value=role.mention if role else "Not found", inline=True)
        embed.add_field(name="Category", value=category.name if category else "Not found", inline=True)
        
        # Get and display actual channels
        category_channels = self.course_service.get_category_channels(ctx.guild, course.category_id)
        embed.add_field(name="Channels", value=f"{len(category_channels)} found", inline=True)
        
        # List the actual channels
        if category_channels:
            channel_list = []
            for channel_info in category_channels[:10]:  # Limit to first 10 to avoid embed limits
                type_emoji = {
                    'text': '💬',
                    'voice': '🔊',
                    'forum': '📋',
                    'stage_voice': '🎭'
                }.get(channel_info['type'], '📁')
                
                channel_list.append(f"{type_emoji} {channel_info['name']}")
            
            if len(category_channels) > 10:
                channel_list.append(f"... and {len(category_channels) - 10} more")
            
            embed.add_field(
                name="Channel List", 
                value="\n".join(channel_list) if channel_list else "None found", 
                inline=False
            )
        
        if course.welcome_message:
            embed.add_field(name="Welcome Message", value=course.welcome_message[:500], inline=False)
        
        # Show student count if roster is loaded
        students = self.course_service.get_course_students(course.name)
        if students:
            enrolled = len([s for s in students if s.status == "enrolled"])
            pending = len([s for s in students if s.status == "pending"])
            embed.add_field(name="Students", value=f"Enrolled: {enrolled}, Pending: {pending}", inline=False)
        
        await ctx.send(embed=embed)
    
    @course_group.command(name='debug')
    @monitor_command()
    async def debug_course(self, ctx, *, name: str = None):
        """Debug course lookup process."""
        if name:
            # Test the exact lookup process
            normalized = self.course_service._normalize_course_name(name)
            course = self.course_service.get_course(name)
            
            embed = discord.Embed(title="Course Lookup Debug", color=0xff9900)
            embed.add_field(name="Input", value=f"'{name}'", inline=True)
            embed.add_field(name="Normalized", value=f"'{normalized}'", inline=True)
            embed.add_field(name="Found", value="Yes" if course else "No", inline=True)
            
            # Show internal storage
            all_courses = self.course_service._courses
            storage_info = []
            for key, config in all_courses.items():
                storage_info.append(f"Key: '{key}' → Name: '{config.name}'")
            
            embed.add_field(name="Internal Storage", 
                           value="\n".join(storage_info) if storage_info else "Empty", 
                           inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("Usage: `!course debug \"Course Name\"`")
    
    # Roster Management Commands
    @commands.group(name='roster', invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def roster_group(self, ctx):
        """Roster management commands."""
        await ctx.send("Use `!roster load`, `!roster status`, or `!roster pending`")
    
    @roster_group.command(name='load')
    @monitor_command()
    async def load_roster(self, ctx, *, csv_content: str = None):
        """Load student roster from CSV content.
        
        Expected CSV format:
        email,name,discord_handle,course_name,enrolled_date,status
        
        Example:
        !roster load
        ```
        email,name,discord_handle,course_name
        john@example.com,John Doe,johndoe,Test Course
        ```
        """
        # Check if this is a backend channel
        if not self.course_service.is_backend_channel(ctx.channel.id):
            await ctx.send("❌ Roster uploads are only allowed in backend channels.")
            return
        
        if not csv_content:
            await ctx.send("❌ Please provide CSV content after the command or in a code block.")
            return
        
        # Clean up the CSV content (remove code block markers if present)
        csv_content = csv_content.strip()
        if csv_content.startswith('```'):
            csv_content = '\n'.join(csv_content.split('\n')[1:-1])
        
        # Load the roster
        success, message = await self.course_service.load_roster_from_text(csv_content)
        
        if success:
            # Process existing members after loading
            await self._process_existing_members(ctx)
            
            # Show summary
            summary = self.course_service.get_roster_summary()
            embed = discord.Embed(title="📊 Roster Loaded Successfully", color=0x00ff00)
            embed.add_field(name="Total Students", value=str(summary['total_students']), inline=True)
            embed.add_field(name="Courses", value=str(len(summary['by_course'])), inline=True)
            
            # Status breakdown
            status_text = []
            for status, count in summary['by_status'].items():
                status_text.append(f"{status}: {count}")
            embed.add_field(name="Status", value="\n".join(status_text), inline=True)
            
            # Course breakdown
            course_text = []
            for course, count in summary['by_course'].items():
                course_text.append(f"{course}: {count}")
            embed.add_field(name="By Course", value="\n".join(course_text), inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {message}")
    
    @roster_group.command(name='status')
    @monitor_command()
    async def roster_status(self, ctx, course_name: str = None):
        """Show roster status for a course or all courses."""
        if course_name:
            students = self.course_service.get_course_students(course_name)
            if not students:
                await ctx.send(f"❌ No students found for course '{course_name}'")
                return
            
            enrolled = len([s for s in students if s.status == "enrolled"])
            pending = len([s for s in students if s.status == "pending"])
            
            embed = discord.Embed(title=f"Roster Status - {course_name}", color=0x0099ff)
            embed.add_field(name="Total", value=str(len(students)), inline=True)
            embed.add_field(name="Enrolled", value=str(enrolled), inline=True)
            embed.add_field(name="Pending", value=str(pending), inline=True)
            
            # Show some pending students
            pending_students = [s for s in students if s.status == "pending"][:5]
            if pending_students:
                pending_list = [f"• {s.name} (@{s.discord_handle})" for s in pending_students]
                if len(pending_students) < pending:
                    pending_list.append(f"... and {pending - len(pending_students)} more")
                embed.add_field(name="Pending Students", value="\n".join(pending_list), inline=False)
        else:
            summary = self.course_service.get_roster_summary()
            if summary['total_students'] == 0:
                await ctx.send("📋 No roster loaded yet. Use `!roster load` to upload student data.")
                return
            
            embed = discord.Embed(title="Overall Roster Status", color=0x0099ff)
            embed.add_field(name="Total Students", value=str(summary['total_students']), inline=True)
            embed.add_field(name="Courses", value=str(len(summary['by_course'])), inline=True)
            embed.add_field(name="Configured", value=str(summary['configured_courses']), inline=True)
            
            # Status breakdown
            status_text = []
            for status, count in summary['by_status'].items():
                status_text.append(f"{status}: {count}")
            embed.add_field(name="Status Breakdown", value="\n".join(status_text), inline=True)
            
            # Course breakdown
            course_text = []
            for course, count in summary['by_course'].items():
                course_text.append(f"{course}: {count}")
            embed.add_field(name="By Course", value="\n".join(course_text), inline=True)
        
        await ctx.send(embed=embed)
    
    @roster_group.command(name='pending')
    @monitor_command()
    async def roster_pending(self, ctx):
        """Show students who haven't been assigned roles yet."""
        pending = self.course_service.get_pending_students()
        
        if not pending:
            await ctx.send("✅ No pending students! Everyone has been assigned roles.")
            return
        
        embed = discord.Embed(title=f"Pending Students ({len(pending)})", color=0xff9900)
        
        # Group by course
        by_course = {}
        for student in pending:
            if student.course_name not in by_course:
                by_course[student.course_name] = []
            by_course[student.course_name].append(student)
        
        for course, students in by_course.items():
            student_list = [f"• {s.name} (@{s.discord_handle})" for s in students[:5]]
            if len(students) > 5:
                student_list.append(f"... and {len(students) - 5} more")
            
            embed.add_field(
                name=f"{course} ({len(students)} pending)",
                value="\n".join(student_list),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @roster_group.command(name='assign')
    @monitor_command()
    async def manual_assign(self, ctx, user: discord.Member, *, course_name: str):
        """Manually assign a course role to a user."""
        course = self.course_service.get_course(course_name)
        if not course:
            await ctx.send(f"❌ Course '{course_name}' not found.")
            return
        
        role = ctx.guild.get_role(course.role_id)
        if not role:
            await ctx.send(f"❌ Role for course '{course_name}' not found.")
            return
        
        try:
            await user.add_roles(role, reason=f"Manual assignment by {ctx.author}")
            
            # Update student record if they're in the roster
            await self.course_service.update_student_discord_id(str(user), user.id)
            
            await ctx.send(f"✅ Assigned {role.mention} to {user.mention}")
            
        except discord.HTTPException as e:
            await ctx.send(f"❌ Failed to assign role: {e}")

    @roster_group.command(name='debug')
    @monitor_command()
    async def debug_roster(self, ctx, *, course_name: str = None):
        """Debug roster data in memory."""
        if course_name:
            students = self.course_service.get_course_students(course_name)

            embed = discord.Embed(title="Roster Debug", color=0xff9900)
            embed.add_field(name="Course Name", value=f"'{course_name}'", inline=True)
            embed.add_field(name="Normalized", value=f"'{course_name.lower().strip()}'", inline=True)
            embed.add_field(name="Students Found", value=str(len(students)), inline=True)

            # Show what's actually stored
            all_students = self.course_service._students
            stored_courses = set()
            for s in all_students:
                stored_courses.add(f"'{s.course_name}' -> '{s.course_name.lower()}'")

            embed.add_field(name="Stored Courses", value="\n".join(stored_courses) if stored_courses else "None", inline=False)

            if students:
                student_list = [f"• {s.name} (@{s.discord_handle})" for s in students[:5]]
                embed.add_field(name="Found Students", value="\n".join(student_list), inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send("Usage: `!roster debug \"Course Name\"`")

    @roster_group.command(name='debuguser')
    @monitor_command()
    async def debug_user(self, ctx, *, discord_handle: str = None):
        """Debug user matching in roster."""
        if not discord_handle:
            discord_handle = str(ctx.author)

        # Try to find the student
        student = self.course_service.find_student_by_discord(discord_handle)

        embed = discord.Embed(title="User Debug", color=0xff9900)
        embed.add_field(name="Discord Handle Input", value=f"'{discord_handle}'", inline=True)
        embed.add_field(name="Normalized", value=f"'{discord_handle.lower().strip()}'", inline=True)
        embed.add_field(name="Found in Roster", value="Yes" if student else "No", inline=True)

        if student:
            embed.add_field(name="Student Info", 
                           value=f"Name: {student.name}\nEmail: {student.email}\nCourse: {student.course_name}", 
                           inline=False)

        # Show what's actually stored
        all_students = self.course_service._students
        stored_handles = [f"'{s.discord_handle}'" for s in all_students]
        embed.add_field(name="All Stored Handles", value="\n".join(stored_handles[:10]), inline=False)

        await ctx.send(embed=embed)
    
    @course_group.command(name='channels')
    @monitor_command()
    async def debug_channels(self, ctx, *, course_name: str):
        """Debug which channels are scanned for a course."""
        course = self.course_service.get_course(course_name)
        if not course:
            await ctx.send(f"❌ Course '{course_name}' not found.")
            return
        
        channels = self.course_service.get_category_channels(ctx.guild, course.category_id)
        
        embed = discord.Embed(title=f"Channels for {course.name}", color=0x0099ff)
        embed.add_field(name="Category ID", value=str(course.category_id), inline=True)
        embed.add_field(name="Channels Found", value=str(len(channels)), inline=True)
        
        if channels:
            channel_list = []
            for ch in channels:
                perms = ch['channel_obj'].permissions_for(ctx.guild.me)
                can_read = "✅" if perms.read_message_history else "❌"
                channel_list.append(f"{can_read} {ch['name']} ({ch['type']})")
            
            embed.add_field(name="Channel List", value="\n".join(channel_list), inline=False)
        
        await ctx.send(embed=embed)

    # Health Check Command
    @commands.command(name='healthcheck')
    @commands.has_permissions(administrator=True)
    @monitor_command()
    async def health_check(self, ctx, *, course_name: str):
        """Run health check for a course to analyze student activity.
        
        Example: !healthcheck "Test Course"
        """
        # Check if this is a backend channel
        if not self.course_service.is_backend_channel(ctx.channel.id):
            await ctx.send("❌ Health checks are only allowed in backend channels.")
            return
        
        # Send initial message
        progress_msg = await ctx.send(f"🔍 Starting health check for **{course_name}**...")
        
        async def update_progress(message):
            try:
                await progress_msg.edit(content=message)
            except discord.HTTPException:
                pass
        
        # Run the health check
        success, message, activities = await self.course_service.run_health_check(
            ctx.guild, course_name, update_progress
        )
        
        if not success:
            await progress_msg.edit(content=f"❌ {message}")
            await ctx.send(f"Debug info: {message}")
            return
        
        # Create results embed
        embed = discord.Embed(
            title=f"📊 Health Check Results: {course_name}",
            description=f"Activity analysis for {len(activities)} students (last 30 days)",
            color=0x0099ff
        )
        
        # Group by activity tier
        by_tier = {}
        for activity in activities:
            tier = activity.activity_tier
            if tier not in by_tier:
                by_tier[tier] = []
            by_tier[tier].append(activity)
        
        # Show tier summaries first
        tier_colors = {
            "At Risk": "🔴",
            "Low Activity": "🟡", 
            "Active": "🟢"
        }
        
        summary_lines = []
        for tier in ["At Risk", "Low Activity", "Active"]:
            if tier in by_tier:
                count = len(by_tier[tier])
                summary_lines.append(f"{tier_colors[tier]} {tier}: {count} students")
        
        embed.add_field(name="Summary", value="\n".join(summary_lines), inline=False)
        
        # Show detailed breakdown for each tier
        for tier in ["At Risk", "Low Activity", "Active"]:
            if tier not in by_tier:
                continue
            
            students = by_tier[tier]
            if not students:
                continue
            
            # Limit to avoid embed size limits
            show_count = min(10, len(students))
            student_lines = []
            
            for activity in students[:show_count]:
                student = activity.student
                
                # Format line
                line = f"• **{student.name}** (@{student.discord_handle})"
                line += f" - {activity.total_messages} total, {activity.messages_last_week} this week"
                
                # Add context
                if activity.member_since:
                    days_ago = (ctx.message.created_at - activity.member_since.replace(tzinfo=None)).days
                    line += f" (joined {days_ago}d ago)"
                
                student_lines.append(line)
            
            if len(students) > show_count:
                student_lines.append(f"... and {len(students) - show_count} more")
            
            field_name = f"{tier_colors[tier]} {tier} ({len(students)})"
            embed.add_field(
                name=field_name,
                value="\n".join(student_lines) if student_lines else "None",
                inline=False
            )
        
        # Add footer with scan info
        embed.set_footer(text="📅 Last 7 days (Pacific Time) | 📊 Total from last 30 days")
        
        # Update progress message with results
        await progress_msg.edit(content="✅ Health check completed!", embed=embed)
    
    async def _process_existing_members(self, ctx):
        """Process existing server members against the roster."""
        processed = 0
        assigned = 0
        
        for member in ctx.guild.members:
            if member.bot:
                continue
            
            # Try to find student by username
            student = self.course_service.find_student_by_discord(str(member))
            if student and student.status == "pending":
                # Get the course and role
                course = self.course_service.get_course(student.course_name)
                if course:
                    role = ctx.guild.get_role(course.role_id)
                    if role and role not in member.roles:
                        try:
                            await member.add_roles(role, reason="Auto-assignment from roster")
                            await self.course_service.update_student_discord_id(str(member), member.id)
                            assigned += 1
                        except discord.HTTPException:
                            pass
                
                processed += 1
        
        if processed > 0:
            await ctx.send(f"🔄 Processed {processed} existing members, assigned {assigned} roles.")
    
    # Auto-role assignment on member join
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Auto-assign course roles when students join."""
        if member.guild.id not in self.course_service.ALLOWED_COURSE_SERVERS:
            return
        
        if member.bot:
            return
        
        # Check if this person is in our roster
        student = self.course_service.find_student_by_discord(str(member))
        
        if student and student.status == "pending":
            # Get the course and role
            course = self.course_service.get_course(student.course_name)
            if course:
                role = member.guild.get_role(course.role_id)
                if role:
                    try:
                        await member.add_roles(role, reason="Auto-assignment from roster")
                        await self.course_service.update_student_discord_id(str(member), member.id)
                        
                        self.logger.info("auto_enrolled_from_roster",
                                       user_id=member.id,
                                       username=str(member),
                                       course=student.course_name,
                                       email=student.email)
                    except discord.HTTPException as e:
                        self.logger.error("failed_to_assign_role",
                                        user_id=member.id,
                                        course=student.course_name,
                                        error=str(e))


async def setup(bot):
    """Add the Course cog to the bot."""
    await bot.add_cog(Course(bot))