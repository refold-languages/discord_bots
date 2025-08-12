"""
Resources cog for Refold Helper Bot.
Handles video/doc lookup, educational content, resource links, and YouTube processing.
"""

import csv
import os
import asyncio
from datetime import datetime

import discord
from discord.ext import commands

import doclist
from config.constants import VIDEO_LINKS_FILE, CROWDSOURCE_DOCS_FILE
from services import YouTubeService, ProcessingProgress
from core import DataManager
from utils import get_logger, monitor_command, ValidationError, DiscordError


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

    # Resource lookup commands
    @commands.command(name='video')
    async def video(self, ctx, *, query: str):
        """Search for instructional videos by keyword."""
        video_link = self._find_video(query)
        await ctx.send(video_link)

    @commands.command(name='doc', aliases=['crowdsourcedoc', 'resourcedoc'])
    async def doc(self, ctx, *, query: str):
        """Search for documentation by language or topic."""
        doc_link = self._find_doc(query)
        await ctx.send(doc_link)

    # Direct resource links
    @commands.command(hidden=True, aliases=['japanesedoc', 'japandoc'])
    async def jpdoc(self, ctx):
        """Get link to Japanese resources document."""
        await ctx.send(f'{doclist.docjp}')

    # Educational content commands
    @commands.command(aliases=['2L2', 'twol2', 'twoltwo', 'twoLtwo', '2l2'])
    async def twoL2(self, ctx):
        """Information about learning two languages simultaneously."""
        await ctx.send('Learning two languages at the same time is totally possible, but it\'s less efficient than doing one language and then the other. This is because you will lose some time switching between the languages, you\'re more likely to get confused, etc. For more information, watch this video: https://www.youtube.com/watch?v=PlteftANWoE')

    @commands.command(aliases=['STAGE1', 'Stage1', 'StageOne', 'Stage_1'])
    async def stage1(self, ctx):
        """Explanation of Refold Stage 1."""
        await ctx.send('Develop an immersion habit. Study some grammar, find a way to study vocabulary (memrise, quantized, anki etc. ), find content that is compelling and comprehensible ( things you have watched before, subjects that inherently interest you ). When you start sentence mining, you are stage 2a.')

    @commands.command(aliases=['SentenceMine', 'sentence_mine', 'sentencemining', 'sentence_mining'])
    async def sentencemine(self, ctx):
        """Explanation of sentence mining technique."""
        await ctx.send('When you encounter a sentence where either one word is unknown, or you just don\'t understand the grammar. We call that 1T. This sentence may be recorded by making it a card on anki or a physical one. The point is that you are learning words most relevant to your immersion past the first 1k words.')

    @commands.command(aliases=['shadow', 'languageparent', 'langparent'])
    async def shadowing(self, ctx):
        """Explanation of shadowing technique."""
        await ctx.send('The point of this exercise is to practice imitating full native speed to get used to the sounds, rhythm and mannerisms of your language parent (the one you want to most speak like). You can find the article here, <https://refold.la/roadmap/stage-3/b/pronunciation-training>')

    # API Key Management Commands
    @commands.command(name='loadkey')
    @commands.has_permissions(administrator=True)
    @monitor_command()
    async def load_key(self, ctx, service: str, *, api_key: str):
        """
        Load an API key for a service.
        
        Usage: !loadkey deepseek sk-1234567890abcdef
        
        Supported services: deepseek
        """
        # Validate service
        supported_services = ['deepseek']
        if service.lower() not in supported_services:
            await ctx.send(f"❌ Unsupported service. Supported services: {', '.join(supported_services)}")
            return
        
        # Try to delete the command message for security
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        
        try:
            # Store the API key
            success = self.data_manager.store_api_key(service, api_key)
            
            if success:
                await ctx.send(f"✅ API key for **{service}** has been stored securely.", delete_after=10)
                self.logger.info("api_key_stored", service=service, user_id=ctx.author.id)
            else:
                await ctx.send("❌ Failed to store API key. Please try again.", delete_after=10)
                
        except Exception as e:
            self.logger.error("api_key_store_error", service=service, error=str(e))
            await ctx.send("❌ An error occurred while storing the API key.", delete_after=10)

    @commands.command(name='listkeys')
    @commands.has_permissions(administrator=True)
    async def list_keys(self, ctx):
        """List all stored API keys (service names only)."""
        try:
            services = self.data_manager.list_api_keys()
            
            if not services:
                await ctx.send("📋 No API keys stored.")
                return
            
            embed = discord.Embed(title="Stored API Keys", color=0x00ff00)
            embed.add_field(
                name="Services",
                value="\n".join(f"• {service}" for service in services),
                inline=False
            )
            embed.set_footer(text="Use !loadkey <service> <key> to add more")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error("list_keys_error", error=str(e))
            await ctx.send("❌ An error occurred while listing API keys.")

    # YouTube to Blog Post Command
    @commands.command(name='youtubetoblog')
    @monitor_command()
    async def youtube_to_blog(self, ctx, *, url: str):
        """
        Convert a YouTube video to a blog post.
        
        Usage: !youtubetoblog https://www.youtube.com/watch?v=VIDEO_ID
        
        This command downloads video subtitles and converts them to a formatted
        blog post using AI. Rate limited to 1 use per hour per user.
        """
        # Validate URL
        if not self.youtube_service.validate_youtube_url(url):
            raise ValidationError("Please provide a valid YouTube URL")
        
        # Check rate limiting
        is_limited, next_allowed = self.youtube_service.is_rate_limited(ctx.author.id)
        if is_limited:
            time_remaining = next_allowed - datetime.now()
            minutes = int(time_remaining.total_seconds() / 60)
            await ctx.send(f"🚫 You're rate limited. Please wait {minutes} minutes before using this command again.")
            return
        
        # Record this request
        self.youtube_service.record_request(ctx.author.id)
        
        # Create thread for processing
        try:
            thread = await ctx.message.create_thread(name="YouTube Blog Conversion")
        except discord.HTTPException as e:
            raise DiscordError("Failed to create thread", discord_error=e)
        
        # Start processing in background
        task = asyncio.create_task(self._process_youtube_video(thread, url))
        
        # Don't await the task - let it run in background
        # The task will handle all updates to the thread
        
        await ctx.send(f"🎬 Started processing video in thread: {thread.mention}")

    async def _process_youtube_video(self, thread, url):
        """Process YouTube video in background with progress updates."""
        typing_task = None
        temp_files = []
        
        try:
            # Send initial message and start typing
            await thread.send("🎬 Creating blog post from video. This can take a while, depending on the length of the video.")
            
            # Start typing indicator
            typing_task = asyncio.create_task(self._keep_typing(thread))
            
            # Progress callback function
            async def progress_callback(progress: ProcessingProgress):
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
            blog_content, video_title, file_path = await self.youtube_service.process_youtube_video(
                url, progress_callback
            )
            temp_files.append(file_path)
            
            # Stop typing
            if typing_task:
                typing_task.cancel()
                typing_task = None
            
            # Send success message
            await thread.send("✅ Blog post conversion completed! Posting content...")
            
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
            try:
                with open(file_path, 'rb') as f:
                    discord_file = discord.File(f, filename=os.path.basename(file_path))
                    await thread.send("📎 **Download as file:**", file=discord_file)
            except Exception as e:
                self.logger.error("file_upload_failed", error=str(e))
                await thread.send("⚠️ Failed to upload file attachment, but content is shown above.")
            
            self.logger.info("youtube_conversion_completed",
                           url=url,
                           title=video_title,
                           thread_id=thread.id)
            
        except ValidationError as e:
            if typing_task:
                typing_task.cancel()
            await thread.send(f"❌ **Validation Error:** {e.user_message}")
            self.logger.warning("youtube_validation_error", url=url, error=str(e))
            
        except Exception as e:
            if typing_task:
                typing_task.cancel()
            
            # Handle different error types
            if "subtitles" in str(e).lower():
                await thread.send("❌ **Error:** No subtitles found for this video. The video needs English subtitles to be processed.")
            elif "deepseek" in str(e).lower():
                await thread.send("❌ **Error:** Failed to process with AI. Please check that the Deepseek API key is configured correctly.")
            else:
                await thread.send(f"❌ **Error:** {str(e)}")
            
            self.logger.error("youtube_conversion_failed", url=url, error=str(e))
        
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
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def avatar(self, ctx, target: discord.Member = None):
        """Get avatar URL for a user."""
        if target is None:
            await ctx.send(f'{ctx.author.avatar}')
        else:
            await ctx.send(f'{target.avatar}')

async def setup(bot):
    """Add the Resources cog to the bot."""
    await bot.add_cog(Resources(bot))