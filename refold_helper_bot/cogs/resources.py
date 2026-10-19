"""
Resources cog for Refold Helper Bot.
Handles video/doc lookup, educational content, resource links, and YouTube processing.
"""

import csv
import os
import asyncio
import traceback
from datetime import datetime

from typing import List

import discord
from discord import app_commands
from discord.ext import commands

import doclist
from config.constants import VIDEO_LINKS_FILE, CROWDSOURCE_DOCS_FILE
from services import YouTubeService, ProcessingProgress
from core import DataManager
from utils import get_logger, monitor_command, ValidationError, DiscordError, DataError

SUPPORTED_KEY_SERVICES = ['deepseek']


class ApiKeyModal(discord.ui.Modal):
    """Collects an API key privately, so it never appears in a channel."""

    api_key = discord.ui.TextInput(label='API key', placeholder='sk-...', max_length=200)

    def __init__(self, cog: 'Resources', service: str):
        super().__init__(title=f'Store {service} API key')
        self.cog = cog
        self.service = service

    async def on_submit(self, interaction: discord.Interaction):
        try:
            success = self.cog.data_manager.store_api_key(self.service, self.api_key.value.strip())
        except Exception as e:
            self.cog.logger.error("api_key_store_error", service=self.service, error=str(e))
            success = False

        if success:
            self.cog.logger.info("api_key_stored", service=self.service, user_id=interaction.user.id)
            await interaction.response.send_message(
                f"✅ API key for **{self.service}** has been stored securely.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Failed to store API key. Please try again.", ephemeral=True)


class Resources(commands.Cog):
    """Commands for accessing learning resources and educational content."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger('cogs.resources')
        self.video_data = self._load_video_data()
        self.doc_data = self._load_docs_data()
        self.youtube_service = YouTubeService()
        self.data_manager = DataManager()
    
    async def cog_load(self):
        """Initialize services when cog loads."""
        self.youtube_service.initialize()
        self.logger.info("resources_cog_loaded")
    
    def _load_video_data(self):
        """Load video reference data from TSV file."""
        videos = []
        try:
            with open(VIDEO_LINKS_FILE, 'r') as file:
                reader = csv.DictReader(file, delimiter='\t', fieldnames=['title', 'references', 'link'])
                for row in reader:
                    row['references'] = row['references'].lower().split(', ')
                    videos.append(row)
        except FileNotFoundError:
            print(f"Warning: {VIDEO_LINKS_FILE} not found")
        return videos
    
    def _load_docs_data(self):
        """Load documentation reference data from TSV file."""
        docs = []
        try:
            with open(CROWDSOURCE_DOCS_FILE, 'r') as file:
                reader = csv.DictReader(file, delimiter='\t', fieldnames=['title', 'references', 'link'])
                for row in reader:
                    row['references'] = row['references'].lower().split(', ')
                    docs.append(row)
        except FileNotFoundError:
            print(f"Warning: {CROWDSOURCE_DOCS_FILE} not found")
        return docs
    
    def _find_video(self, query):
        """Find video by query in references."""
        query = query.lower()
        for video in self.video_data:
            if query in video['references']:
                return video['link']
        return "No video found for your query."
    
    def _find_doc(self, query):
        """Find documentation by query in references."""
        query = query.lower()
        for doc in self.doc_data:
            if query in doc['references']:
                return doc['link']
        return "No document found for your query."

    @staticmethod
    def _autocomplete_references(entries, current: str) -> List[app_commands.Choice[str]]:
        """Suggest lookup keywords from a resource table's reference lists."""
        current = current.lower()
        seen = []
        for entry in entries:
            for ref in entry['references']:
                if ref and current in ref and ref not in seen:
                    seen.append(ref)
        return [app_commands.Choice(name=ref[:100], value=ref[:100]) for ref in seen[:25]]

    # Resource lookup commands
    @app_commands.command(name='video', description='Search for instructional videos by keyword')
    @app_commands.describe(query='Topic keyword')
    async def video(self, interaction: discord.Interaction, query: str):
        """Search for instructional videos by keyword."""
        await interaction.response.send_message(self._find_video(query))

    @video.autocomplete('query')
    async def _video_autocomplete(self, interaction: discord.Interaction, current: str):
        return self._autocomplete_references(self.video_data, current)

    @app_commands.command(name='doc', description='Find the crowdsourced resource doc for a language or topic')
    @app_commands.describe(query='Language or topic')
    async def doc(self, interaction: discord.Interaction, query: str):
        """Search for documentation by language or topic."""
        await interaction.response.send_message(self._find_doc(query))

    @doc.autocomplete('query')
    async def _doc_autocomplete(self, interaction: discord.Interaction, current: str):
        return self._autocomplete_references(self.doc_data, current)

    # Direct resource links
    @app_commands.command(description='Link to the Japanese resources document')
    async def jpdoc(self, interaction: discord.Interaction):
        """Get link to Japanese resources document."""
        await interaction.response.send_message(f'{doclist.docjp}')

    # Educational content commands
    @app_commands.command(name='twol2', description='Learning two languages at the same time')
    async def twoL2(self, interaction: discord.Interaction):
        """Information about learning two languages simultaneously."""
        await interaction.response.send_message('Learning two languages at the same time is totally possible, but it\'s less efficient than doing one language and then the other. This is because you will lose some time switching between the languages, you\'re more likely to get confused, etc. For more information, watch this video: https://www.youtube.com/watch?v=PlteftANWoE')

    @app_commands.command(description='What Refold Stage 1 is about')
    async def stage1(self, interaction: discord.Interaction):
        """Explanation of Refold Stage 1."""
        await interaction.response.send_message('Develop an immersion habit. Study some grammar, find a way to study vocabulary (memrise, quantized, anki etc. ), find content that is compelling and comprehensible ( things you have watched before, subjects that inherently interest you ). When you start sentence mining, you are stage 2a.')

    @app_commands.command(description='What sentence mining is')
    async def sentencemine(self, interaction: discord.Interaction):
        """Explanation of sentence mining technique."""
        await interaction.response.send_message('When you encounter a sentence where either one word is unknown, or you just don\'t understand the grammar. We call that 1T. This sentence may be recorded by making it a card on anki or a physical one. The point is that you are learning words most relevant to your immersion past the first 1k words.')

    @app_commands.command(description='What shadowing is')
    async def shadowing(self, interaction: discord.Interaction):
        """Explanation of shadowing technique."""
        await interaction.response.send_message('The point of this exercise is to practice imitating full native speed to get used to the sounds, rhythm and mannerisms of your language parent (the one you want to most speak like). You can find the article here, <https://refold.la/roadmap/stage-3/b/pronunciation-training>')

    # API Key Management Commands
    @app_commands.command(name='loadkey', description='Store an API key for a service (opens a private form)')
    @app_commands.describe(service='Which service the key is for')
    @app_commands.choices(service=[app_commands.Choice(name=s, value=s) for s in SUPPORTED_KEY_SERVICES])
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def load_key(self, interaction: discord.Interaction, service: app_commands.Choice[str]):
        """Load an API key for a service via a modal, so the key is never posted."""
        await interaction.response.send_modal(ApiKeyModal(self, service.value))

    @app_commands.command(name='listkeys', description='List stored API keys (service names only)')
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def list_keys(self, interaction: discord.Interaction):
        """List all stored API keys (service names only)."""
        try:
            services = self.data_manager.list_api_keys()
            
            if not services:
                await interaction.response.send_message("📋 No API keys stored.", ephemeral=True)
                return
            
            embed = discord.Embed(title="Stored API Keys", color=0x00ff00)
            embed.add_field(
                name="Services",
                value="\n".join(f"• {service}" for service in services),
                inline=False
            )
            embed.set_footer(text="Use /loadkey to add more")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            self.logger.error("list_keys_error", error=str(e))
            await interaction.response.send_message("❌ An error occurred while listing API keys.", ephemeral=True)

    # YouTube to Blog Post Command
    @app_commands.command(name='youtubetoblog', description='Convert a YouTube video into a blog post')
    @app_commands.describe(url='YouTube video URL')
    @app_commands.guild_only()
    @monitor_command()
    async def youtube_to_blog(self, interaction: discord.Interaction, url: str):
        """
        Convert a YouTube video to a blog post.
        
        Usage: /youtubetoblog url:https://www.youtube.com/watch?v=VIDEO_ID
        
        This command downloads video subtitles and converts them to a formatted
        blog post using AI. Rate limited to 1 use per hour per user.
        """
        # Validate URL
        if not self.youtube_service.validate_youtube_url(url):
            raise ValidationError("Please provide a valid YouTube URL")
        
        # Check rate limiting
        is_limited, next_allowed = self.youtube_service.is_rate_limited(interaction.user.id)
        if is_limited:
            time_remaining = next_allowed - datetime.now()
            minutes = int(time_remaining.total_seconds() / 60)
            await interaction.response.send_message(
                f"🚫 You're rate limited. Please wait {minutes} minutes before using this command again.",
                ephemeral=True)
            return
        
        # Record this request
        self.youtube_service.record_request(interaction.user.id)
        
        # Create a thread on our own reply - there is no command message to hang it on
        await interaction.response.send_message(f"🎬 Converting <{url}> to a blog post...")
        try:
            message = await interaction.original_response()
            thread = await message.create_thread(name="YouTube Blog Conversion")
        except discord.HTTPException as e:
            raise DiscordError("Failed to create thread", discord_error=e)
        
        # Start processing in background; the task handles all updates to the thread
        asyncio.create_task(self._process_youtube_video(thread, url))
        
        await interaction.edit_original_response(
            content=f"🎬 Started processing video in thread: {thread.mention}")

    async def _process_youtube_video(self, thread, url):
        """Process YouTube video in background with progress updates."""
        typing_task = None
        temp_files = []
        current_stage = "initialization"
        
        try:
            # Send initial message and start typing
            await thread.send("🎬 Creating blog post from video. This can take a while, depending on the length of the video.")
            current_stage = "initialization"
            
            # Start typing indicator
            typing_task = asyncio.create_task(self._keep_typing(thread))
            
            # Progress callback function
            async def progress_callback(progress: ProcessingProgress):
                nonlocal current_stage
                current_stage = progress.stage
                if progress.stage == "info":
                    await thread.send(f"📺 {progress.message}")
                elif progress.stage == "processing":
                    if progress.estimated_time:
                        await thread.send(f"📊 {progress.message}\n⏱️ Estimated processing time: {progress.estimated_time}")
                    else:
                        await thread.send(f"📊 {progress.message}")
                else:
                    await thread.send(f"🔄 {progress.message}")
            
            # Process the video
            current_stage = "video_processing"
            self.logger.info("youtube_conversion_started",
                           url=url,
                           thread_id=thread.id,
                           stage=current_stage)
            
            blog_content, video_title, file_path = await self.youtube_service.process_youtube_video(
                url, progress_callback
            )
            temp_files.append(file_path)
            current_stage = "content_preparation"
            
            # Stop typing
            if typing_task:
                typing_task.cancel()
                typing_task = None
            
            # Send success message
            await thread.send("✅ Blog post conversion completed! Posting content...")
            current_stage = "content_posting"
            
            # Split content for Discord messages
            message_chunks = self.youtube_service.split_message_for_discord(blog_content)
            
            # Send content in chunks
            for i, chunk in enumerate(message_chunks):
                if i == 0:
                    await thread.send(f"📝 **Blog Post Content:**\n\n{chunk}")
                else:
                    await thread.send(chunk)
                
                # Small delay between messages to avoid rate limits
                await asyncio.sleep(0.5)
            
            # Send file attachment
            current_stage = "file_upload"
            try:
                with open(file_path, 'rb') as f:
                    discord_file = discord.File(f, filename=os.path.basename(file_path))
                    await thread.send("📎 **Download as file:**", file=discord_file)
            except Exception as e:
                self.logger.error("file_upload_failed",
                               url=url,
                               error=str(e),
                               error_type=type(e).__name__,
                               stack_trace=traceback.format_exc())
                await thread.send("⚠️ Failed to upload file attachment, but content is shown above.")
            
            self.logger.info("youtube_conversion_completed",
                           url=url,
                           title=video_title,
                           thread_id=thread.id,
                           final_stage=current_stage)
            
        except ValidationError as e:
            if typing_task:
                typing_task.cancel()
            
            self.logger.error("youtube_validation_error",
                           url=url,
                           stage=current_stage,
                           error=str(e),
                           error_type=type(e).__name__,
                           user_message=e.user_message,
                           stack_trace=traceback.format_exc())
            
            await thread.send(f"❌ **Validation Error:** {e.user_message}")
            
        except DataError as e:
            if typing_task:
                typing_task.cancel()
            
            self.logger.error("youtube_data_error",
                           url=url,
                           stage=current_stage,
                           error=str(e),
                           error_type=type(e).__name__,
                           user_message=e.user_message,
                           stack_trace=traceback.format_exc())
            
            # Provide more specific error messages based on stage
            if current_stage == "video_processing":
                if "subtitles" in str(e).lower() or "subtitle" in str(e).lower():
                    await thread.send("❌ **Error:** No subtitles found for this video. The video needs subtitles to be processed.")
                elif "deepseek" in str(e).lower() or "api" in str(e).lower():
                    await thread.send("❌ **Error:** Failed to process with AI. Please check that the Deepseek API key is configured correctly.")
                else:
                    await thread.send(f"❌ **Error:** {e.user_message}")
            else:
                await thread.send(f"❌ **Error:** {e.user_message}")
            
        except Exception as e:
            if typing_task:
                typing_task.cancel()
            
            error_type = type(e).__name__
            error_message = str(e)
            stack_trace = traceback.format_exc()
            
            self.logger.error("youtube_conversion_failed",
                           url=url,
                           stage=current_stage,
                           error=error_message,
                           error_type=error_type,
                           stack_trace=stack_trace)
            
            # Handle different error types with more context
            if "subtitles" in error_message.lower() or "subtitle" in error_message.lower():
                await thread.send("❌ **Error:** No subtitles found for this video. The video needs subtitles to be processed.")
            elif "deepseek" in error_message.lower() or "api" in error_message.lower():
                await thread.send("❌ **Error:** Failed to process with AI. Please check that the Deepseek API key is configured correctly.")
            elif "timeout" in error_message.lower():
                await thread.send(f"❌ **Error:** The request timed out. This might be due to a very long video or API issues. Please try again later.")
            else:
                await thread.send(f"❌ **Error:** {error_message}")
        
        finally:
            # Clean up temporary files
            for file_path in temp_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        self.logger.debug("temp_file_cleaned", file_path=file_path)
                except Exception as e:
                    self.logger.warning("temp_file_cleanup_failed", file_path=file_path, error=str(e))
            
            # Stop typing if still running
            if typing_task:
                typing_task.cancel()

    async def _keep_typing(self, channel):
        """Keep the typing indicator active during long operations."""
        try:
            while True:
                async with channel.typing():
                    await asyncio.sleep(8)  # Discord typing lasts ~10 seconds
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.warning("typing_indicator_error", error=str(e))

    # Utility commands
    @app_commands.command(description="Get a user's avatar URL")
    @app_commands.describe(target='Whose avatar (default: yours)')
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def avatar(self, interaction: discord.Interaction, target: discord.User = None):
        """Get avatar URL for a user."""
        user = target or interaction.user
        await interaction.response.send_message(user.display_avatar.url)

async def setup(bot):
    """Add the Resources cog to the bot."""
    await bot.add_cog(Resources(bot))