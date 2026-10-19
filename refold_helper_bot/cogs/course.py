"""
Course management cog for Refold Helper Bot.
Handles course configuration and student management for the learning platform.
"""

import asyncio
from datetime import timezone
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from services import CourseService
from utils import get_logger, monitor_command, ValidationError, DiscordError
from utils.interactions import respond, confirm, read_text_attachment

# Discord allows one member-search gateway request per guild every 30 seconds.
MEMBER_QUERY_INTERVAL_SECONDS = 31
# Pending students looked up per guild on each background pass.
MEMBER_QUERY_BATCH = 10


class EnrollView(discord.ui.View):
    """Persistent "get my course role" button for course welcome channels.

    Survives restarts (timeout=None + fixed custom_id, re-registered in
    cog_load). It lets students enroll themselves, which needs no privileged
    intent: the button press tells us exactly who they are.
    """

    def __init__(self, cog: 'Course'):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label='Get my course role', style=discord.ButtonStyle.primary,
                       custom_id='refold:course:enroll')
    async def enroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.self_enroll(interaction)


class Course(commands.Cog):
    """Course management for the Refold learning platform."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.course')
        self.course_service = CourseService()
    
    async def cog_load(self):
        """Initialize the course service when cog loads."""
        self.course_service.initialize()
        self.bot.add_view(EnrollView(self))
        self.resolve_pending_students.start()
        self.logger.info("course_cog_loaded")

    async def cog_unload(self):
        self.resolve_pending_students.cancel()
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Course commands only work in the allowed course servers."""
        if interaction.guild_id is None or not self.course_service.is_course_server(interaction.guild_id):
            raise app_commands.CheckFailure("Course commands are not enabled in this server.")
        return True

    async def _course_name_autocomplete(self, interaction: discord.Interaction,
                                        current: str) -> List[app_commands.Choice[str]]:
        current = current.lower()
        names = [c.name for c in self.course_service.get_all_courses().values()
                 if current in c.name.lower()]
        return [app_commands.Choice(name=n[:100], value=n[:100]) for n in names[:25]]

    course_group = app_commands.Group(
        name='course', description='Course configuration',
        default_permissions=discord.Permissions(administrator=True), guild_only=True)
    roster_group = app_commands.Group(
        name='roster', description='Student roster management',
        default_permissions=discord.Permissions(administrator=True), guild_only=True)

    # Course Configuration Commands
    @course_group.command(name='add', description='Add a new course configuration')
    @app_commands.describe(name='Course name', role='Role students of the course get',
                           category='Category holding the course channels')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def add_course(self, interaction: discord.Interaction, name: str, role: discord.Role,
                         category: discord.CategoryChannel):
        """Add a new course configuration."""
        success, message = await self.course_service.add_course(name, role.id, category.id)
        
        if success:
            await interaction.response.send_message(f"✅ {message}")
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
    
    @course_group.command(name='remove', description='Remove a course configuration')
    @app_commands.describe(name='Course to remove')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def remove_course(self, interaction: discord.Interaction, name: str):
        """Remove a course configuration."""
        guild = interaction.guild
        # First check if course exists
        course = self.course_service.get_course(name)
        if not course:
            available_courses = list(self.course_service.get_all_courses().keys())
            error_msg = f"❌ Course '{name}' not found."
            if available_courses:
                error_msg += f"\nAvailable courses: {', '.join(available_courses)}"
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        # Confirm removal
        embed = discord.Embed(
            title="⚠️ Confirm Course Removal",
            description=f"Are you sure you want to remove course **{course.name}**?",
            color=0xff9900
        )
        
        role = guild.get_role(course.role_id)
        category = guild.get_channel(course.category_id)
        
        embed.add_field(name="Role", value=role.mention if role else "Not found", inline=True)
        embed.add_field(name="Category", value=category.name if category else "Not found", inline=True)
        
        # Get channel count
        category_channels = self.course_service.get_category_channels(guild, course.category_id)
        embed.add_field(name="Channels", value=f"{len(category_channels)} channels", inline=True)
        
        embed.add_field(
            name="⚠️ Warning", 
            value="This will only remove the course from bot configuration.\nDiscord roles and channels will NOT be deleted.",
            inline=False
        )
        
        if not await confirm(interaction, None, embed=embed, timeout=30.0, confirm_label='Remove course'):
            return

        success, result_message = await self.course_service.remove_course(name)
        if success:
            await respond(interaction, f"✅ {result_message}", ephemeral=True)
        else:
            await respond(interaction, f"❌ {result_message}", ephemeral=True)
    
    @course_group.command(name='list', description='List all configured courses')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def list_courses(self, interaction: discord.Interaction):
        """List all configured courses."""
        guild = interaction.guild
        courses = self.course_service.get_all_courses()
        
        if not courses:
            await interaction.response.send_message("No courses configured yet.", ephemeral=True)
            return
        
        embed = discord.Embed(title="Configured Courses", color=0x00ff00)
        
        for course in courses.values():
            role = guild.get_role(course.role_id)
            category = guild.get_channel(course.category_id)
            
            # Get actual channels in the category
            category_channels = self.course_service.get_category_channels(guild, course.category_id)
            
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
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @course_group.command(name='info', description='Detailed info about a course')
    @app_commands.describe(name='Course name')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def course_info(self, interaction: discord.Interaction, name: str):
        """Get detailed info about a specific course."""
        guild = interaction.guild
        course = self.course_service.get_course(name)
        
        if not course:
            available = [c.name for c in self.course_service.get_all_courses().values()]
            await interaction.response.send_message(
                f"❌ Course '{name}' not found.\nAvailable courses: {', '.join(available) or 'none'}",
                ephemeral=True)
            return
        
        embed = discord.Embed(title=f"Course: {course.name}", color=0x0099ff)
        
        role = guild.get_role(course.role_id)
        category = guild.get_channel(course.category_id)
        
        embed.add_field(name="Role", value=role.mention if role else "Not found", inline=True)
        embed.add_field(name="Category", value=category.name if category else "Not found", inline=True)
        
        # Get and display actual channels
        category_channels = self.course_service.get_category_channels(guild, course.category_id)
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
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @course_group.command(name='channels', description='Show which channels are scanned for a course')
    @app_commands.describe(course_name='Course name')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def debug_channels(self, interaction: discord.Interaction, course_name: str):
        """Debug which channels are scanned for a course."""
        guild = interaction.guild
        course = self.course_service.get_course(course_name)
        if not course:
            await interaction.response.send_message(f"❌ Course '{course_name}' not found.", ephemeral=True)
            return
        
        channels = self.course_service.get_category_channels(guild, course.category_id)
        
        embed = discord.Embed(title=f"Channels for {course.name}", color=0x0099ff)
        embed.add_field(name="Category ID", value=str(course.category_id), inline=True)
        embed.add_field(name="Channels Found", value=str(len(channels)), inline=True)
        
        if channels:
            channel_list = []
            for ch in channels:
                perms = ch['channel_obj'].permissions_for(guild.me)
                can_read = "✅" if perms.read_message_history else "❌"
                channel_list.append(f"{can_read} {ch['name']} ({ch['type']})")
            
            embed.add_field(name="Channel List", value="\n".join(channel_list)[:1024], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @course_group.command(name='enrollbutton',
                          description='Post a "Get my course role" button for students')
    @app_commands.describe(channel='Channel to post the button in (default: this one)')
    @app_commands.checks.has_permissions(administrator=True)
    async def post_enroll_button(self, interaction: discord.Interaction,
                                 channel: Optional[discord.TextChannel] = None):
        """Post the persistent self-enrollment button."""
        target = channel or interaction.channel
        await target.send(
            "👋 **Enrolled in a Refold course?** Press the button to get access to your course "
            "channels. Your Discord username needs to match the one you gave when you signed up.",
            view=EnrollView(self))
        await interaction.response.send_message(f"✅ Posted the enrollment button in {target.mention}.",
                                                ephemeral=True)

    # Roster Management Commands
    @roster_group.command(name='load', description='Load the student roster from a CSV file')
    @app_commands.describe(file='CSV with columns: email,name,discord_handle,course_name[,enrolled_date,status]')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def load_roster(self, interaction: discord.Interaction, file: discord.Attachment):
        """Load student roster from an uploaded CSV file.
        
        Expected CSV format:
        email,name,discord_handle,course_name,enrolled_date,status
        """
        # Check if this is a backend channel
        if not self.course_service.is_backend_channel(interaction.channel_id):
            await interaction.response.send_message("❌ Roster uploads are only allowed in backend channels.",
                                                    ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        try:
            csv_content = (await read_text_attachment(file)).strip()
        except ValueError as e:
            await respond(interaction, f"❌ {e}")
            return
        
        # Load the roster
        success, message = await self.course_service.load_roster_from_text(csv_content)
        
        if success:
            # Process existing members after loading
            await self._process_existing_members(interaction)
            
            # Show summary
            summary = self.course_service.get_roster_summary()
            embed = discord.Embed(title="📊 Roster Loaded Successfully", color=0x00ff00)
            embed.add_field(name="Total Students", value=str(summary['total_students']), inline=True)
            embed.add_field(name="Courses", value=str(len(summary['by_course'])), inline=True)
            
            # Status breakdown
            status_text = []
            for status, count in summary['by_status'].items():
                status_text.append(f"{status}: {count}")
            embed.add_field(name="Status", value="\n".join(status_text) or "-", inline=True)
            
            # Course breakdown
            course_text = []
            for course, count in summary['by_course'].items():
                course_text.append(f"{course}: {count}")
            embed.add_field(name="By Course", value="\n".join(course_text)[:1024] or "-", inline=False)
            
            await respond(interaction, embed=embed)
        else:
            await respond(interaction, f"❌ {message}")
    
    @roster_group.command(name='status', description='Roster status for one course or all courses')
    @app_commands.describe(course_name='Course name (default: all courses)')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def roster_status(self, interaction: discord.Interaction, course_name: Optional[str] = None):
        """Show roster status for a course or all courses."""
        if course_name:
            students = self.course_service.get_course_students(course_name)
            if not students:
                await interaction.response.send_message(f"❌ No students found for course '{course_name}'",
                                                        ephemeral=True)
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
                await interaction.response.send_message(
                    "📋 No roster loaded yet. Use `/roster load` to upload student data.", ephemeral=True)
                return
            
            embed = discord.Embed(title="Overall Roster Status", color=0x0099ff)
            embed.add_field(name="Total Students", value=str(summary['total_students']), inline=True)
            embed.add_field(name="Courses", value=str(len(summary['by_course'])), inline=True)
            embed.add_field(name="Configured", value=str(summary['configured_courses']), inline=True)
            
            # Status breakdown
            status_text = []
            for status, count in summary['by_status'].items():
                status_text.append(f"{status}: {count}")
            embed.add_field(name="Status Breakdown", value="\n".join(status_text) or "-", inline=True)
            
            # Course breakdown
            course_text = []
            for course, count in summary['by_course'].items():
                course_text.append(f"{course}: {count}")
            embed.add_field(name="By Course", value="\n".join(course_text)[:1024] or "-", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @roster_group.command(name='pending', description="Students who haven't been assigned roles yet")
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def roster_pending(self, interaction: discord.Interaction):
        """Show students who haven't been assigned roles yet."""
        pending = self.course_service.get_pending_students()
        
        if not pending:
            await interaction.response.send_message("✅ No pending students! Everyone has been assigned roles.",
                                                    ephemeral=True)
            return
        
        embed = discord.Embed(title=f"Pending Students ({len(pending)})", color=0xff9900)
        
        # Group by course
        by_course = {}
        for student in pending:
            if student.course_name not in by_course:
                by_course[student.course_name] = []
            by_course[student.course_name].append(student)
        
        for course, students in list(by_course.items())[:25]:
            student_list = [f"• {s.name} (@{s.discord_handle})" for s in students[:5]]
            if len(students) > 5:
                student_list.append(f"... and {len(students) - 5} more")
            
            embed.add_field(
                name=f"{course} ({len(students)} pending)",
                value="\n".join(student_list),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @roster_group.command(name='assign', description='Manually assign a course role to a user')
    @app_commands.describe(user='Student', course_name='Course name')
    @app_commands.checks.has_permissions(administrator=True)
    @monitor_command()
    async def manual_assign(self, interaction: discord.Interaction, user: discord.Member, course_name: str):
        """Manually assign a course role to a user."""
        course = self.course_service.get_course(course_name)
        if not course:
            await interaction.response.send_message(f"❌ Course '{course_name}' not found.", ephemeral=True)
            return
        
        role = interaction.guild.get_role(course.role_id)
        if not role:
            await interaction.response.send_message(f"❌ Role for course '{course_name}' not found.",
                                                    ephemeral=True)
            return
        
        try:
            await user.add_roles(role, reason=f"Manual assignment by {interaction.user}")
            
            # Update student record if they're in the roster
            await self.course_service.update_student_discord_id(str(user), user.id)
            
            await interaction.response.send_message(f"✅ Assigned {role.mention} to {user.mention}",
                                                    allowed_mentions=discord.AllowedMentions.none())
            
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Failed to assign role: {e}", ephemeral=True)

    @remove_course.autocomplete('name')
    @course_info.autocomplete('name')
    @debug_channels.autocomplete('course_name')
    @roster_status.autocomplete('course_name')
    @manual_assign.autocomplete('course_name')
    async def _course_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._course_name_autocomplete(interaction, current)

    # Health Check Command
    @app_commands.command(name='healthcheck', description="Analyse students' activity in a course")
    @app_commands.describe(course_name='Course name')
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    @monitor_command()
    async def health_check(self, interaction: discord.Interaction, course_name: str):
        """Run health check for a course to analyze student activity."""
        # Check if this is a backend channel
        if not self.course_service.is_backend_channel(interaction.channel_id):
            await interaction.response.send_message("❌ Health checks are only allowed in backend channels.",
                                                    ephemeral=True)
            return
        
        # Send initial message
        await interaction.response.send_message(f"🔍 Starting health check for **{course_name}**...")
        
        async def update_progress(message):
            try:
                await interaction.edit_original_response(content=message)
            except discord.HTTPException:
                pass
        
        # Run the health check
        success, message, activities = await self.course_service.run_health_check(
            interaction.guild, course_name, update_progress
        )
        
        if not success:
            await interaction.edit_original_response(content=f"❌ {message}")
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
        
        embed.add_field(name="Summary", value="\n".join(summary_lines) or "No students", inline=False)
        
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
                    member_since = activity.member_since
                    if member_since.tzinfo is None:
                        member_since = member_since.replace(tzinfo=timezone.utc)
                    days_ago = (interaction.created_at - member_since).days
                    line += f" (joined {days_ago}d ago)"
                
                student_lines.append(line)
            
            if len(students) > show_count:
                student_lines.append(f"... and {len(students) - show_count} more")
            
            field_name = f"{tier_colors[tier]} {tier} ({len(students)})"
            embed.add_field(
                name=field_name,
                value="\n".join(student_lines)[:1024] if student_lines else "None",
                inline=False
            )
        
        # Add footer with scan info
        embed.set_footer(text="📅 Last 7 days (Pacific Time) | 📊 Total from last 30 days")
        
        # Update progress message with results
        await interaction.edit_original_response(content="✅ Health check completed!", embed=embed)

    @health_check.autocomplete('course_name')
    async def _healthcheck_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._course_name_autocomplete(interaction, current)
    
    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------
    async def _enroll(self, guild: discord.Guild, member: discord.Member, student,
                      *, source: str) -> Optional[discord.Role]:
        """Give a roster student their course role. Returns the role on success."""
        course = self.course_service.get_course(student.course_name)
        role = guild.get_role(course.role_id) if course else None
        if role is None:
            self.logger.warning("enroll_course_role_missing", course=student.course_name,
                                guild_id=guild.id)
            return None
        try:
            if role not in member.roles:
                await member.add_roles(role, reason=f"Course enrollment from roster ({source})")
        except discord.HTTPException as e:
            self.logger.error("failed_to_assign_role", user_id=member.id,
                              course=student.course_name, error=str(e))
            return None
        await self.course_service.update_student_discord_id(student.discord_handle, member.id)
        self.logger.info("auto_enrolled_from_roster", user_id=member.id, username=str(member),
                         course=student.course_name, source=source)
        return role

    def _pending_student_for(self, member):
        return self.course_service.find_pending_student(
            username=member.name, display=str(member))

    async def self_enroll(self, interaction: discord.Interaction):
        """Shared body of /enroll and the enrollment button."""
        guild = interaction.guild
        if guild is None or not self.course_service.is_course_server(guild.id):
            await interaction.response.send_message("Course enrollment isn't available here.",
                                                    ephemeral=True)
            return
        student = self._pending_student_for(interaction.user)
        if student is None:
            await interaction.response.send_message(
                "I couldn't find a pending enrollment for your Discord username "
                f"(`{interaction.user.name}`). If you've already been enrolled you're all set; "
                "otherwise please contact a coach so they can check the roster.", ephemeral=True)
            return
        role = await self._enroll(guild, interaction.user, student, source='self-serve')
        if role is None:
            await interaction.response.send_message(
                "Something went wrong giving you your course role. Please contact a coach.",
                ephemeral=True)
            return
        await interaction.response.send_message(
            f"✅ Welcome to **{student.course_name}**! You now have the {role.mention} role.",
            ephemeral=True)

    @app_commands.command(name='enroll', description='Get your course role if you are on the roster')
    @app_commands.guild_only()
    async def enroll(self, interaction: discord.Interaction):
        """Self-serve course enrollment."""
        await self.self_enroll(interaction)

    async def _process_existing_members(self, interaction: discord.Interaction):
        """Process existing server members against the roster.

        Relies on the member cache, so it only finds anyone when the Guild
        Members intent is enabled; otherwise students are picked up by the
        enrollment button, /enroll, and the background resolver.
        """
        if not self.bot.intents.members:
            await respond(interaction, "ℹ️ Without the Guild Members intent I can't scan existing "
                                       "members now - students can press the enrollment button "
                                       "(`/course enrollbutton`), and I'll also look them up in the "
                                       "background over the next while.")
            return

        processed = 0
        assigned = 0
        guild = interaction.guild

        for member in guild.members:
            if member.bot:
                continue
            student = self._pending_student_for(member)
            if student:
                processed += 1
                if await self._enroll(guild, member, student, source='roster load'):
                    assigned += 1

        if processed > 0:
            await respond(interaction, f"🔄 Processed {processed} existing members, assigned {assigned} roles.")

    @tasks.loop(minutes=15)
    async def resolve_pending_students(self):
        """Find pending students who are already in the server, without the members intent.

        Looks each one up by username with a member search, which needs no
        privileged intent but is limited to one request per guild every 30
        seconds - so this works through the roster slowly, a batch at a time.
        """
        if self.bot.intents.members:
            return  # on_member_join and roster-load scans cover it
        for guild_id in self.course_service.ALLOWED_COURSE_SERVERS:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue
            pending = self.course_service.get_pending_students()[:MEMBER_QUERY_BATCH]
            for student in pending:
                query = student.discord_handle.lstrip('@').split('#')[0]
                if not query:
                    continue
                try:
                    candidates = await guild.query_members(query=query, limit=5)
                except (asyncio.TimeoutError, discord.HTTPException) as e:
                    self.logger.warning("pending_student_query_failed", guild_id=guild.id,
                                        error=str(e), error_type=type(e).__name__)
                    candidates = []
                for member in candidates:
                    if not member.bot and self.course_service.handle_matches(
                            student.discord_handle, username=member.name, display=str(member)):
                        await self._enroll(guild, member, student, source='background lookup')
                        break
                await asyncio.sleep(MEMBER_QUERY_INTERVAL_SECONDS)

    @resolve_pending_students.before_loop
    async def _before_resolve(self):
        await self.bot.wait_until_ready()

    # Auto-role assignment on member join (needs the Guild Members intent)
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Auto-assign course roles when students join."""
        if member.guild.id not in self.course_service.ALLOWED_COURSE_SERVERS:
            return
        if member.bot:
            return
        student = self._pending_student_for(member)
        if student:
            await self._enroll(member.guild, member, student, source='member join')


async def setup(bot):
    """Add the Course cog to the bot."""
    await bot.add_cog(Course(bot))