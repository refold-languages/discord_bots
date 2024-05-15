import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os
import re
import asyncio
from dotenv import load_dotenv
import replicate
import argparse
import string

load_dotenv()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(intents=intents, command_prefix='!')

allowed_channels = {'1237175445682786304': 'yt-subs-generator', '1240007483196702821': 'subtitle-gen'}
subtitles_dir = 'subtitles'
os.makedirs(subtitles_dir, exist_ok=True)

@bot.event
async def on_ready():
    print('Bot is ready!')

@bot.event
async def on_message(message):
    if str(message.channel.id) in allowed_channels:
        if "youtube.com/watch?" in message.content or "youtu.be/" in message.content or "youtube.com/playlist?" in message.content:
            try:
                url = extract_url(message.content)
                if not url:
                    await message.channel.send("No valid URL found in the message.")
                    return

                if "youtube.com/playlist?" in url:
                    thread = await message.create_thread(name="Playlist Subtitles")
                    await thread.send("Checking for playlist subtitles. Give me a moment, this can take a while.")
                    video_urls = extract_video_urls_from_playlist(url)
                    if not video_urls:
                        await thread.send("No videos found in the playlist.")
                        return

                    for video_url in video_urls:
                        await process_video(thread, video_url, skip_checks=False)
                else:
                    thread = await message.create_thread(name="Video Subtitles")
                    await thread.send("Checking for subtitles. Give me a moment.")
                    await process_video(thread, url, skip_checks=False)

            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")
        await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    
    channel = bot.get_channel(payload.channel_id)
    if str(channel.id) in allowed_channels:
        message = await channel.fetch_message(payload.message_id)
        if payload.emoji.name == '📝':
            if "youtube.com/watch?" in message.content or "youtu.be/" in message.content or "youtube.com/playlist?" in message.content:
                try:
                    url = extract_url(message.content)
                    if not url:
                        await channel.send("No valid URL found in the message.")
                        return

                    thread = None
                    active_threads = channel.threads
                    for active_thread in active_threads:
                        if active_thread.id == payload.message_id:
                            thread = active_thread
                            break

                    if thread is None:
                        if "youtube.com/playlist?" in url:
                            thread = await message.create_thread(name="Playlist Subtitles")
                        else:
                            thread = await message.create_thread(name="Video Subtitles")

                    await thread.send("Starting transcription process. This can take a while.")

                    if "youtube.com/playlist?" in url:
                        video_urls = extract_video_urls_from_playlist(url)
                        if not video_urls:
                            await thread.send("No videos found in the playlist.")
                            return

                        for video_url in video_urls:
                            await process_video(thread, video_url, skip_checks=True)
                    else:
                        await process_video(thread, url, skip_checks=True)

                except Exception as e:
                    await channel.send(f"An error occurred: {e}")

def fetch_video_title(url):
    try:
        ydl_opts = {'skip_download': True}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            return result.get('title', 'Unknown Video Title')
    except Exception as e:
        raise RuntimeError(f"Failed to fetch video title: {e}")

def sanitize_title(title):
    invalid_chars_pattern = r'[<>:"/\\|?*\x00-\x1F]'
    sanitized_title = re.sub(invalid_chars_pattern, '_', title)
    return sanitized_title

def download_subtitles_from_video(url, video_title):
    try:
        ydl_opts = {
            'writesubtitles': True,
            'skip_download': True,
            'subtitleslangs': [],
            'outtmpl': f'{subtitles_dir}/{video_title}.%(ext)s'
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            if 'subtitles' in result and result['subtitles']:
                default_language = list(result['subtitles'].keys())[0]
                ydl_opts['subtitleslangs'] = [default_language]
                with youtube_dl.YoutubeDL(ydl_opts) as ydl_default:
                    ydl_default.download([url])
                
                remove_json_subtitle_files(video_title)
                
                subtitle_file = find_subtitle_file(video_title)
                return subtitle_file
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to download YouTube subtitles: {e}")

def remove_json_subtitle_files(video_title):
    try:
        for file in os.listdir(subtitles_dir):
            if file.startswith(video_title) and file.endswith('.json'):
                os.remove(os.path.join(subtitles_dir, file))
    except Exception as e:
        raise RuntimeError(f"Failed to remove JSON subtitle files: {e}")

def find_subtitle_file(video_title):
    try:
        for file in os.listdir(subtitles_dir):
            if video_title in file:
                return os.path.join(subtitles_dir, file)
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to find subtitle file: {e}")

def extract_url(message_content):
    url_pattern = r'(https?://\S+)'
    match = re.search(url_pattern, message_content)
    return match.group(0) if match else None

def extract_video_urls_from_playlist(playlist_url):
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True
    }
    video_urls = []
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(playlist_url, download=False)
        for entry in info_dict['entries']:
            video_urls.append(entry['url'])
    return video_urls

async def process_video(thread, video_url, skip_checks=False):
    video_title = sanitize_title(fetch_video_title(video_url))
    
    if not skip_checks:
        if video_title:
            file_found = False
            for file_name in os.listdir(subtitles_dir):
                if video_title in file_name:
                    subtitles_file_path = os.path.join(subtitles_dir, file_name)
                    file_found = True
                    with open(subtitles_file_path, 'rb') as file:
                        await thread.send(f'Subtitles found for {video_title}.')
                        await thread.send(file=discord.File(file, f'{video_title}.srt'))
                    break

            if file_found:
                return

            subtitles_file_path = download_subtitles_from_video(video_url, video_title)
            if subtitles_file_path:
                with open(subtitles_file_path, 'rb') as file:
                    await thread.send(f'Subtitles found for {video_title}.')
                    await thread.send(file=discord.File(file, f'{video_title}.vtt'))
            else:
                await thread.send(f'The creator didn\'t add subtitles for {video_title}. I will generate them now. Please be patient, this can take several minutes.')
                await async_transcribe_and_notify(video_url, video_title, thread)
        else:
            return
    else:
        await async_transcribe_and_notify(video_url, video_title, thread)

async def async_transcribe_and_notify(video_url, video_title, thread):
    try:
        subtitles_file_path = await youtube_video_to_srt_async(video_url, video_title)
        if subtitles_file_path:
            with open(subtitles_file_path, 'rb') as file:
                await thread.send(file=discord.File(file, f'{video_title}.srt'))
        else:
            await thread.send("An error occurred while generating subtitles. Please try again later.")
    except Exception as e:
        await thread.send(f"An error occurred while transcribing the audio: {e}")

async def youtube_video_to_srt_async(video_url, video_title):
    try:
        audio_filename = await download_audio_async(video_url)
        if not audio_filename:
            return None
        transcription = await transcribe_audio_with_replicate_async(audio_filename)
        if not transcription:
            return None
        srt_filename = generate_srt(transcription, video_title)
        return srt_filename
    except Exception as e:
        raise RuntimeError(f"Failed to generate SRT: {e}")

async def download_audio_async(video_url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True
        }
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(video_url, download=True))
        filename = youtube_dl.YoutubeDL(ydl_opts).prepare_filename(info)
        return filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
    except Exception as e:
        raise RuntimeError(f"Failed to download audio: {e}")

async def transcribe_audio_with_replicate_async(audio_file):
    try:
        input = {
            "audio_file": open(audio_file, "rb"),
            "debug": False,
            "vad_onset": 0.3,
            "batch_size": 64,
            "vad_offset": 0.3,
            "diarization": False,
            "temperature": 0,
            "align_output": True,
            "language_detection_min_prob": 0,
            "language_detection_max_tries": 5
        }
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, lambda: replicate.run(
            "victor-upmeet/whisperx:826801120720e563620006b99e412f7ed7b991dd4477e9160473d44a405ef9d9",
            input=input
        ))
        os.remove(audio_file)
        return output
    except Exception as e:
        raise RuntimeError(f"Failed to transcribe audio: {e}")

def generate_srt(transcription, video_title):
    try:
        srt_filename = f'{subtitles_dir}/{video_title}.srt'
        with open(srt_filename, 'w') as file:
            for i, segment in enumerate(transcription['segments'], start=1):
                start_time = format_time(segment['start'])
                end_time = format_time(segment['end'])
                text = segment['text']
                file.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")
        return srt_filename
    except Exception as e:
        raise RuntimeError(f"Failed to generate SRT file: {e}")

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:06.3f}".replace('.', ',')

parser = argparse.ArgumentParser()
parser.add_argument('auth_key', type=str, help='the key to authenticate this discord bot with discord')
args = parser.parse_args()

bot.run(args.auth_key)