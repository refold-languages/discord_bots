"""
YouTube service for Refold Helper Bot.
Handles YouTube video processing and blog post conversion.
"""

import os
import re
import json
import asyncio
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import aiohttp
import discord

from .base_service import BaseService
from core import DataManager
from utils import get_logger, ValidationError, DataError, safe_execute

@dataclass
class VideoInfo:
    """Information about a YouTube video."""
    title: str
    duration: Optional[str] = None
    view_count: Optional[int] = None
    upload_date: Optional[str] = None

@dataclass
class ProcessingProgress:
    """Progress tracking for video processing."""
    stage: str
    message: str
    word_count: Optional[int] = None
    estimated_time: Optional[str] = None

class YouTubeService(BaseService):
    """Service for processing YouTube videos into blog posts."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('services.youtube')
        self.data_manager = DataManager()
        self._rate_limits: Dict[int, datetime] = {}  # user_id -> last_request_time
        self.rate_limit_hours = 1  # 1 request per hour per user
    
    def initialize(self) -> None:
        super().initialize()
        self.logger.info("youtube_service_initializing")
    
    def is_rate_limited(self, user_id: int) -> Tuple[bool, Optional[datetime]]:
        """
        Check if user is rate limited.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (is_limited, next_allowed_time)
        """
        if user_id not in self._rate_limits:
            return False, None
        
        last_request = self._rate_limits[user_id]
        next_allowed = last_request + timedelta(hours=self.rate_limit_hours)
        
        if datetime.now() >= next_allowed:
            return False, None
        
        return True, next_allowed
    
    def record_request(self, user_id: int):
        """Record a request for rate limiting."""
        self._rate_limits[user_id] = datetime.now()
    
    def validate_youtube_url(self, url: str) -> bool:
        """Validate that URL is a YouTube URL."""
        youtube_patterns = [
            r'youtube\.com/watch\?v=',
            r'youtu\.be/',
            r'youtube\.com/embed/',
            r'youtube\.com/v/'
        ]
        
        return any(re.search(pattern, url) for pattern in youtube_patterns)
    
    async def get_video_info(self, url: str) -> Optional[VideoInfo]:
        """
        Get basic information about a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            VideoInfo object or None if failed
        """
        try:
            # Only use supported options - get title and duration
            cmd = [
                'yt-dlp',
                '--get-title',
                '--get-duration',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--no-warnings',
                url
            ]
            
            # Create a wrapper function to properly handle subprocess call
            def run_subprocess():
                return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_subprocess)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self.logger.error("video_info_failed", 
                                url=url, 
                                return_code=result.returncode,
                                error=error_msg,
                                stdout=result.stdout.strip() if result.stdout else "")
                return None
            
            lines = result.stdout.strip().split('\n')
            
            self.logger.info("video_info_success", 
                           url=url,
                           title=lines[0] if len(lines) > 0 else "Unknown")
            
            return VideoInfo(
                title=lines[0] if len(lines) > 0 else "Unknown Title",
                duration=lines[1] if len(lines) > 1 else None,
                view_count=None,  # Not available with current yt-dlp options
                upload_date=None  # Not available with current yt-dlp options
            )
            
        except FileNotFoundError as e:
            self.logger.error("yt_dlp_not_found", url=url, error=str(e))
            raise ValidationError("yt-dlp is not installed or not accessible. Please install it with: pip install yt-dlp")
        except subprocess.TimeoutExpired as e:
            self.logger.error("video_info_timeout", url=url, error=str(e))
            return None
        except Exception as e:
            self.logger.error("video_info_exception", url=url, error=str(e), error_type=type(e).__name__)
            return None
    
    async def download_subtitles(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Download subtitles from YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Tuple of (subtitle_content, video_title) or (None, None) if failed
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Try auto-generated subtitles first
                cmd = [
                    'yt-dlp',
                    '--write-auto-subs',
                    '--sub-lang', 'en',
                    '--sub-format', 'srt',
                    '--skip-download',
                    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    '--output', f'{temp_dir}/%(title)s.%(ext)s',
                    '--no-warnings',
                    url
                ]
                
                # Create wrapper function for subprocess call
                def run_subprocess():
                    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, run_subprocess)
                
                # If auto-subs failed, try manual subtitles
                if result.returncode != 0:
                    self.logger.info("auto_subs_failed_trying_manual", 
                                   url=url, 
                                   error=result.stderr.strip() if result.stderr else "Unknown")
                    cmd[1] = '--write-subs'  # Change to manual subs
                    result = await loop.run_in_executor(None, run_subprocess)
                
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                    self.logger.error("subtitle_download_failed", 
                                    url=url, 
                                    return_code=result.returncode,
                                    error=error_msg)
                    
                    # Check for common error patterns
                    if "no subtitles" in error_msg.lower() or "no automatic captions" in error_msg.lower():
                        raise ValidationError("This video doesn't have English subtitles available.")
                    elif "private" in error_msg.lower():
                        raise ValidationError("This video is private or unavailable.")
                    elif "geo" in error_msg.lower() or "blocked" in error_msg.lower():
                        raise ValidationError("This video is geo-blocked or restricted.")
                    else:
                        raise ValidationError(f"Failed to download subtitles: {error_msg}")
                
                # Find subtitle file
                subtitle_files = list(Path(temp_dir).glob('*.srt'))
                if not subtitle_files:
                    self.logger.warning("no_subtitle_files_found", url=url)
                    raise ValidationError("No subtitle files were downloaded.")
                
                # Get video title
                title_cmd = [
                    'yt-dlp',
                    '--get-title',
                    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    '--no-warnings',
                    url
                ]
                
                def run_title_subprocess():
                    return subprocess.run(title_cmd, capture_output=True, text=True, timeout=30)
                
                title_result = await loop.run_in_executor(None, run_title_subprocess)
                video_title = title_result.stdout.strip() if title_result.returncode == 0 else "Unknown Title"
                
                # Read subtitle content
                with open(subtitle_files[0], 'r', encoding='utf-8') as f:
                    subtitle_content = f.read()
                
                self.logger.info("subtitles_downloaded_successfully", 
                               url=url, title=video_title, content_length=len(subtitle_content))
                
                return subtitle_content, video_title
                
            except FileNotFoundError as e:
                self.logger.error("yt_dlp_not_found_subtitles", url=url, error=str(e))
                raise ValidationError("yt-dlp is not installed or not accessible. Please install it with: pip install yt-dlp")
            except ValidationError:
                # Re-raise validation errors as-is
                raise
            except Exception as e:
                self.logger.error("subtitle_download_exception", url=url, error=str(e), error_type=type(e).__name__)
                raise ValidationError(f"Unexpected error downloading subtitles: {str(e)}")
    
    def clean_srt_subtitles(self, srt_content: str) -> str:
        """
        Convert SRT subtitle format to clean text.
        
        Args:
            srt_content: Raw SRT subtitle content
            
        Returns:
            Cleaned text content
        """
        if not srt_content:
            return ""
        
        lines = srt_content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip SRT sequence numbers, timestamps, and empty lines
            if (line.isdigit() or 
                '-->' in line or
                not line):
                continue
            
            # Remove HTML tags
            line = re.sub(r'<[^>]+>', '', line)
            
            # Remove any remaining timestamp markers
            line = re.sub(r'\d{2}:\d{2}:\d{2}[,\.]\d{3}', '', line)
            
            if line:
                text_lines.append(line)
        
        # Join lines and clean up
        text = ' '.join(text_lines)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def estimate_processing_time(self, word_count: int) -> str:
        """Estimate processing time based on word count."""
        if word_count < 1000:
            return "1-2 minutes"
        elif word_count < 3000:
            return "2-4 minutes"
        elif word_count < 5000:
            return "3-6 minutes"
        else:
            return "5-10 minutes"
    
    def _cleanup_deepseek_response(self, content: str) -> str:
        """
        Clean up Deepseek API response by removing markdown code block wrappers.
        
        Args:
            content: Raw response content
            
        Returns:
            Cleaned content
        """
        if not content:
            return content
        
        cleaned = content.strip()
        
        # Remove ```markdown from the beginning (safe to remove)
        if cleaned.startswith('```markdown'):
            cleaned = cleaned[len('```markdown'):].strip()
        
        # Remove ``` from the end only if it's at the very end
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3].strip()
        
        return cleaned

    async def call_deepseek_api(self, text: str, video_title: str) -> Optional[str]:
        """
        Call Deepseek API to convert transcript to blog post.
        
        Args:
            text: Cleaned transcript text
            video_title: Original video title
            
        Returns:
            Formatted blog post or None if failed
        """
        api_key = self.data_manager.get_api_key("deepseek")
        if not api_key:
            raise DataError("Deepseek API key not found. Use !loadkey deepseek <key> to set it.")
        
        prompt = f"""You are tasked with converting a YouTube video transcript into a well-formatted markdown blog post. 

The video title is: "{video_title}"

Please clean up this transcript by:
1. Removing filler words (uh, um, you know, etc.) that are only part of spoken language
2. Fixing grammar and adding punctuation for readability
3. Adding appropriate headings and sections, using language the original author used
4. Keeping all the original content and arguments, as they are presented
5. Making it read like a professional blog post rather than a transcript
6. Without adding any additional information, making up additions or cutting out parts of the video
7. Use the video title as the main heading
8. At the bottom of the post, add a TLDR summary, but note that it is AI generated

Here's the transcript:

{text}

Please format this as a clean, readable markdown blog post. Include no other content in your output, only the post."""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000,
            "temperature": 0.3
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.deepseek.com/v1/chat/completions", 
                                      headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error("deepseek_api_error", 
                                        status=response.status, 
                                        error=error_text)
                        raise DataError(f"Deepseek API returned status {response.status}")
                    
                    result = await response.json()
                    raw_content = result['choices'][0]['message']['content']
                    
                    # Clean up the response to remove markdown code block wrappers
                    blog_content = self._cleanup_deepseek_response(raw_content)
                    
                    self.logger.info("deepseek_api_success", 
                                   input_length=len(text),
                                   output_length=len(blog_content),
                                   cleanup_applied=len(raw_content) != len(blog_content))
                    
                    return blog_content
                    
        except aiohttp.ClientError as e:
            self.logger.error("deepseek_api_client_error", error=str(e))
            raise DataError(f"Failed to connect to Deepseek API: {str(e)}")
        except KeyError as e:
            self.logger.error("deepseek_api_response_error", error=str(e))
            raise DataError("Unexpected response from Deepseek API")
        except Exception as e:
            self.logger.error("deepseek_api_unexpected_error", error=str(e))
            raise DataError(f"Deepseek API error: {str(e)}")
    
    def split_message_for_discord(self, content: str, max_length: int = 2000) -> List[str]:
        """
        Split long content into Discord message-sized chunks.
        
        Args:
            content: Content to split
            max_length: Maximum length per message
            
        Returns:
            List of message chunks
        """
        if len(content) <= max_length:
            return [content]
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed limit
            if len(current_chunk) + len(paragraph) + 2 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                # If paragraph itself is too long, split by sentences
                if len(paragraph) > max_length:
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 2 > max_length:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = ""
                        current_chunk += sentence + ". "
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def create_markdown_file(self, content: str, video_title: str) -> str:
        """
        Create a markdown file with the blog post content.
        
        Args:
            content: Blog post content
            video_title: Original video title
            
        Returns:
            Path to created file
        """
        # Clean up title for filename
        safe_title = re.sub(r'[^\w\s-]', '', video_title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title[:50]}.md"
        
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.logger.info("markdown_file_created", file_path=file_path)
        return file_path
    
    @safe_execute("process_youtube_video")
    async def process_youtube_video(self, url: str, progress_callback=None) -> Tuple[str, str, str]:
        """
        Process a YouTube video into a blog post.
        
        Args:
            url: YouTube video URL
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (blog_content, video_title, file_path)
        """
        if progress_callback:
            await progress_callback(ProcessingProgress(
                "validation", "Checking video availability..."
            ))
        
        # Get video info
        video_info = await self.get_video_info(url)
        if not video_info:
            raise ValidationError("Could not access video. It may be private, geo-blocked, or invalid.")
        
        if progress_callback:
            duration_text = f" ({video_info.duration})" if video_info.duration else ""
            await progress_callback(ProcessingProgress(
                "info", f"Video found: {video_info.title}{duration_text}"
            ))
        
        # Download subtitles
        if progress_callback:
            await progress_callback(ProcessingProgress(
                "download", "Downloading subtitles..."
            ))
        
        subtitle_content, video_title = await self.download_subtitles(url)
        if not subtitle_content:
            raise ValidationError("No subtitles found for this video. The video needs English subtitles to be processed.")
        
        # Clean subtitles
        clean_text = self.clean_srt_subtitles(subtitle_content)
        if not clean_text:
            raise DataError("No usable text content found in subtitles.")
        
        word_count = len(clean_text.split())
        estimated_time = self.estimate_processing_time(word_count)
        
        if progress_callback:
            await progress_callback(ProcessingProgress(
                "processing", 
                f"Video subtitles include {word_count:,} words. Please be patient while I reformat it.",
                word_count=word_count,
                estimated_time=estimated_time
            ))
        
        # Convert to blog post
        blog_content = await self.call_deepseek_api(clean_text, video_title)
        if not blog_content:
            raise DataError("Failed to convert transcript to blog post.")
        
        # Create file
        file_path = self.create_markdown_file(blog_content, video_title)
        
        self.logger.info("youtube_video_processed_successfully",
                        url=url,
                        title=video_title,
                        word_count=word_count,
                        output_length=len(blog_content))
        
        return blog_content, video_title, file_path