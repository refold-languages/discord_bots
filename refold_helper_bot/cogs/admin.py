"""
Admin cog for Refold Helper Bot.
Contains administrative commands for analytics, bot management, and data migration.
"""

import discord
from discord.ext import commands

from config.constants import COMMUNITY_SERVERS, ALLOWED_ADMIN_USER_IDS, UNIQUE_USERS_FILE
from services import MigrationService


class Admin(commands.Cog):
    """Administrative commands for bot management and analytics."""
    
    def __init__(self, bot):
        self.bot = bot
        self.migration_service = MigrationService()

    async def cog_load(self):
        """Initialize the migration service when cog loads."""
        self.migration_service.initialize()

    @commands.command(help='Checks the ping of the bot.', category='General Commands')
    async def ping(self, ctx):
        """Check bot latency."""
        await ctx.send(f'Pong! The bot\'s latency is {round(self.bot.latency * 1000)}ms')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def count_unique_users(self, ctx):
        """Count unique users across all community servers (admin only)."""
        if ctx.author.id not in ALLOWED_ADMIN_USER_IDS:
            await ctx.send("You don't have permission to use this command.")
            return
            
        unique_users = {}
        for guild_id in COMMUNITY_SERVERS:
            guild = self.bot.get_guild(guild_id)
            if guild: 
                for member in guild.members:
                    if member.id in unique_users:
                        unique_users[member.id]['guild_names'].append(guild.name)
                        if member.joined_at < unique_users[member.id]['joined_at']:
                            unique_users[member.id]['joined_at'] = member.joined_at
                    else:
                        unique_users[member.id] = {
                            'name': member.name,
                            'discriminator': member.discriminator,
                            'guild_names': [guild.name],
                            'joined_at': member.joined_at
                        }
        
        # Write results to TSV file
        with open(UNIQUE_USERS_FILE, 'w', encoding='utf-8') as file:
            file.write("UUID\tName\tDiscriminator\tServer Names\tFirst Joined At\n")
            for user_id, data in unique_users.items():
                server_names = ", ".join(data['guild_names'])
                first_joined_at = data['joined_at'].strftime('%Y-%m-%d %H:%M:%S')
                file.write(f"{user_id}\t{data['name']}\t{data['discriminator']}\t{server_names}\t{first_joined_at}\n")
        
        await ctx.send(f"Unique users counted: {len(unique_users)}")
        await ctx.send(file=discord.File(UNIQUE_USERS_FILE))

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def migrate_data(self, ctx):
        """Migrate legacy data files to new JSON format with schema validation."""
        if ctx.author.id not in ALLOWED_ADMIN_USER_IDS:
            await ctx.send("You don't have permission to use this command.")
            return
        
        # Get migration status first
        status = self.migration_service.get_migration_status()
        
        if not status["needs_migration"]:
            await ctx.send("✅ No legacy files found. All data is already in modern format!")
            
            # Show current data summary
            embed = discord.Embed(title="Data Summary", color=0x00ff00)
            for data_type, info in status["data_summary"].items():
                if info.get("exists", False):
                    embed.add_field(
                        name=data_type.replace("_", " ").title(),
                        value=f"Items: {info.get('item_count', 0)}\nLast Updated: {info.get('last_updated', 'Unknown')}",
                        inline=True
                    )
            await ctx.send(embed=embed)
            return
        
        # Inform about files found
        legacy_files = status["legacy_files_found"]
        await ctx.send(f"🔍 Found {len(legacy_files)} legacy files to migrate:")
        for file_path in legacy_files:
            await ctx.send(f"  • `{file_path}`")
        
        await ctx.send("🚀 Starting migration...")
        
        # Perform migration
        try:
            report = self.migration_service.migrate_all_files()
            
            # Create migration report embed
            embed = discord.Embed(title="Migration Report", color=0x00ff00 if report.failure_count == 0 else 0xff9900)
            
            embed.add_field(name="Files Found", value=str(report.total_found), inline=True)
            embed.add_field(name="Successfully Migrated", value=str(report.success_count), inline=True)
            embed.add_field(name="Failed", value=str(report.failure_count), inline=True)
            
            if report.files_migrated:
                embed.add_field(
                    name="✅ Migrated Files",
                    value="\n".join(f"• {f}" for f in report.files_migrated),
                    inline=False
                )
            
            if report.backups_created:
                embed.add_field(
                    name="💾 Backups Created", 
                    value=f"{len(report.backups_created)} backup files created",
                    inline=False
                )
            
            if report.errors:
                embed.add_field(
                    name="❌ Errors",
                    value="\n".join(report.errors[:5]),  # Limit to first 5 errors
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
            # Validate migration results
            await ctx.send("🔍 Validating migrated data...")
            validation_results = self.migration_service.validate_migration()
            
            all_valid = all(valid for valid, _ in validation_results.values())
            if all_valid:
                await ctx.send("✅ All migrated data passed validation!")
            else:
                await ctx.send("⚠️ Some validation issues found:")
                for data_type, (valid, error) in validation_results.items():
                    if not valid:
                        await ctx.send(f"  • {data_type}: {error}")
        
        except Exception as e:
            await ctx.send(f"❌ Migration failed: {str(e)}")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def migration_status(self, ctx):
        """Check the current migration status and data summary."""
        if ctx.author.id not in ALLOWED_ADMIN_USER_IDS:
            await ctx.send("You don't have permission to use this command.")
            return
        
        try:
            status = self.migration_service.get_migration_status()
            
            # Create status embed
            embed = discord.Embed(
                title="Migration Status", 
                color=0xff9900 if status["needs_migration"] else 0x00ff00
            )
            
            embed.add_field(
                name="Migration Needed",
                value="Yes" if status["needs_migration"] else "No",
                inline=True
            )
            
            embed.add_field(
                name="All Data Valid",
                value="Yes" if status["all_valid"] else "No",
                inline=True
            )
            
            if status["legacy_files_found"]:
                embed.add_field(
                    name="Legacy Files Found",
                    value="\n".join(f"• {f}" for f in status["legacy_files_found"]),
                    inline=False
                )
            
            # Data summary
            data_summary_text = []
            for data_type, info in status["data_summary"].items():
                if info.get("exists", False):
                    count = info.get("item_count", 0)
                    migrated = " (migrated)" if info.get("was_migrated", False) else ""
                    data_summary_text.append(f"• {data_type}: {count} items{migrated}")
                else:
                    data_summary_text.append(f"• {data_type}: Not found")
            
            if data_summary_text:
                embed.add_field(
                    name="Data Summary",
                    value="\n".join(data_summary_text),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error checking migration status: {str(e)}")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def cleanup_legacy(self, ctx, confirm: str = None):
        """Clean up legacy files after successful migration. Use 'confirm' to actually delete."""
        if ctx.author.id not in ALLOWED_ADMIN_USER_IDS:
            await ctx.send("You don't have permission to use this command.")
            return
        
        if confirm != "confirm":
            await ctx.send(
                "⚠️ This command will archive legacy files after migration.\n"
                "Use `!cleanup_legacy confirm` to proceed.\n"
                "**Make sure migration was successful first!**"
            )
            return
        
        try:
            success, message = self.migration_service.cleanup_legacy_files(confirm=True)
            
            if success:
                await ctx.send(f"✅ {message}")
            else:
                await ctx.send(f"❌ {message}")
                
        except Exception as e:
            await ctx.send(f"Error during cleanup: {str(e)}")

    @commands.command(hidden=True)
    @commands.has_permissions(administrator=True)
    async def force_recreate_data(self, ctx, confirm: str = None):
        """DANGER: Force recreate all data files with defaults. This will destroy existing data!"""
        if ctx.author.id not in ALLOWED_ADMIN_USER_IDS:
            await ctx.send("You don't have permission to use this command.")
            return
        
        if confirm != "DESTROY_ALL_DATA":
            await ctx.send(
                "🚨 **DANGER: This will destroy all existing data!** 🚨\n"
                "This command recreates all data files with default values.\n"
                "Use `!force_recreate_data DESTROY_ALL_DATA` if you really want to do this.\n"
                "**This action cannot be undone!**"
            )
            return
        
        try:
            results = self.migration_service.force_recreate_data_files()
            
            embed = discord.Embed(title="Force Recreate Results", color=0xff0000)
            for data_type, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                embed.add_field(name=data_type, value=status, inline=True)
            
            await ctx.send("🔥 All data files have been recreated with defaults!", embed=embed)
            
        except Exception as e:
            await ctx.send(f"Error during force recreate: {str(e)}")


async def setup(bot):
    """Add the Admin cog to the bot."""
    await bot.add_cog(Admin(bot))