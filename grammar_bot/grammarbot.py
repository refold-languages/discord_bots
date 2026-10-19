import discord
from discord import app_commands
from discord.ext import commands
from openai import OpenAI
import argparse
import asyncio
import os
import re


def _read_deepseek_key():
    """DEEPSEEK_API_KEY from the environment, falling back to deepseekapi.txt."""
    key = os.getenv('DEEPSEEK_API_KEY')
    if key:
        return key.strip()
    with open('deepseekapi.txt', 'r') as token_file:
        return token_file.read().strip()


deepseek_key = _read_deepseek_key()

deepseek_client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

# deepseek-v4-flash is DeepSeek's fast, low-cost model. Thinking mode is
# disabled to keep responses quick and cheap.
MODEL = "deepseek-v4-flash"
NON_THINKING = {"thinking": {"type": "disabled"}}

# Grammar-tutor instructions. Sent as a system message on every request so the
# persona and guardrails apply to follow-up messages too, not just the first.
SYSTEM_PROMPT = (
    "You are a specially trained language grammar assistant. Here are your instructions:\n"
    "Role and Goal: You are designed to assist immersion language learners by explaining "
    "grammar concepts. You specialize in breaking down grammatical rules into "
    "understandable chunks, focusing exclusively on comprehension. You explain what grammatical "
    "constructions mean using natural language, practical examples, and simple words in the target language "
    "to aid understanding.\n\nConstraints: You do not use drills, charts, obtuse grammar terms, and "
    "detailed discussions on the creation or application of grammar patterns. If you ever need to use a grammar term, "
    "it should be immediately followed by a plain explanation. You are programmed not to "
    "instruct users on how to use grammar patterns for language improvement but to ensure they grasp the "
    "underlying meaning.\n\nGuidelines: When providing explanations, rely on examples in the "
    "target language, using simple and accessible vocabulary. This approach helps learners intuitively "
    "understand how grammar works in practical contexts. Official grammar terms are introduced sparingly, "
    "and only to offer users paths for further exploration.\n\nPersonalization: You maintain "
    "a supportive and encouraging tone, making grammar learning a less intimidating experience. Your response is tailored "
    "to make grammar approachable, using examples that resonate with learners at all levels.\n"
    "If a user asks a non language related question, respond with *Sorry, I can't answer that question.*\n\n"
    "Response Language (most important rule): Write your entire explanation in the SAME language the "
    "user wrote their question in, even when the question is about a different target language. The "
    "target language is the subject of the question, not the language you answer in. Only the specific "
    "words, phrases, and examples that belong to the target language should appear in the target "
    "language; everything else — your explanations, descriptions, and commentary — must be in the "
    "user's question language. For example, if the user writes in English and asks about two Polish "
    "words, explain the difference in English and only quote the Polish words themselves in Polish. "
    "Never reply entirely in the target language unless the user explicitly asks you to answer in it."
)

# Bot-authored filler lines. Kept as constants so they can be filtered out of
# conversation history when building follow-up requests.
THINKING_MESSAGE = "Allow me a moment to think."
LIMIT_MESSAGE = "This conversation has reached its limit. Please open a new thread to continue."
ERROR_MESSAGE = "Something went wrong. Please try again."
FOLLOWUP_HINT = "-# Follow-up question? Mention me or reply to me in this thread (up to 2)."
MENTION_NEEDED_MESSAGE = ("I can only read messages that mention me. "
                          "Please @mention me with your follow-up question.")
FILLER_MESSAGES = {THINKING_MESSAGE, LIMIT_MESSAGE, ERROR_MESSAGE, FOLLOWUP_HINT,
                   MENTION_NEEDED_MESSAGE}

# Cap on the number of threads we track so the tracking dicts can't grow forever.
MAX_TRACKED_THREADS = 1000
# Follow-up answers allowed per thread after the first answer.
MAX_FOLLOWUPS = 2
ASKED_PREFIX = "asked:**\n"

# No privileged intents: Discord only grants Message Content after review, and
# this bot no longer needs it. Questions arrive through a slash command or the
# message context menu (both carry the text), and follow-ups must mention or
# reply to the bot - Discord delivers the content of those messages anyway.
intents = discord.Intents.default()
bot = commands.Bot(intents=intents, command_prefix=commands.when_mentioned, help_command=None)

channel_list = [1210371437802561637, 1215710869531656192, 1221944946827722832, 1221947610638581924]
thread_message_count = {}
# thread id -> the question that opened it. A thread's starter message lives in
# the parent channel, not the thread, so history alone would lose it.
thread_questions = {}


@bot.event
async def setup_hook():
    synced = await bot.tree.sync()
    print(f'Synced {len(synced)} application commands')


@bot.event
async def on_ready():
    name = bot.user
    print(f'We have logged in as {name}')


def split_message(msg, limit=1999):
    if len(msg) <= limit:
        return [msg]
    chunks = []
    while len(msg) > limit:
        split_at = msg.rfind('. ', 0, limit + 1)
        if split_at == -1:
            split_at = msg.rfind(' ', 0, limit + 1)
        if split_at == -1 or split_at == 0:
            split_at = limit
        else:
            split_at += 1
        chunks.append(msg[:split_at])
        msg = msg[split_at:].lstrip()
    chunks.append(msg)
    return chunks

async def get_completion(messages):
    """Run the (blocking) DeepSeek call off the event loop so the bot stays
    responsive while waiting on the API.

    Returns the reply text, or None if the request fails or comes back empty.
    """
    def _call():
        return deepseek_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            extra_body=NON_THINKING,
        )
    try:
        response = await asyncio.to_thread(_call)
    except Exception as exc:
        print(f"DeepSeek request failed: {exc}")
        return None
    if response.choices and response.choices[0].message:
        return response.choices[0].message.content
    return None


def thread_name_for(question):
    return ' '.join(question.split()[:5])[:100] or 'Grammar question'


def strip_bot_mention(content):
    """Remove @mentions of the bot so the model only sees the question."""
    return re.sub(rf'<@!?{bot.user.id}>', '', content).strip()


def track_thread(thread_id, question):
    # Bound the tracking dicts: evict the oldest entry once we're over the cap.
    if len(thread_message_count) >= MAX_TRACKED_THREADS:
        oldest = next(iter(thread_message_count))
        del thread_message_count[oldest]
        thread_questions.pop(oldest, None)
    thread_message_count[thread_id] = 1
    thread_questions[thread_id] = question


async def answer_in_thread(thread, question):
    """Post the first answer to a new question thread."""
    track_thread(thread.id, question)
    await thread.send(THINKING_MESSAGE)
    async with thread.typing():
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        output = await get_completion(messages)
        if output:
            for chunk in split_message(output):
                await thread.send(chunk)
            await thread.send(FOLLOWUP_HINT)
        else:
            await thread.send(ERROR_MESSAGE)


@bot.tree.command(name='grammar', description='Ask a grammar question - I answer in a new thread')
@app_commands.describe(question='Your question, in any language')
@app_commands.guild_only()
async def grammar(interaction: discord.Interaction,
                  question: app_commands.Range[str, 1, 4000]):
    if interaction.channel_id not in channel_list:
        mentions = ' '.join(f'<#{c}>' for c in channel_list)
        await interaction.response.send_message(
            f"Please ask grammar questions in one of these channels: {mentions}", ephemeral=True)
        return
    # Post the question as our own message and hang the thread off it, so the
    # question stays visible in the channel just like a normal post.
    await interaction.response.send_message(
        f"**{interaction.user.mention} {ASKED_PREFIX}{question}"[:2000],
        allowed_mentions=discord.AllowedMentions.none())
    starter = await interaction.original_response()
    thread = await starter.create_thread(name=thread_name_for(question), auto_archive_duration=60)
    await answer_in_thread(thread, question)


@bot.tree.context_menu(name='Ask Grammar Bot')
@app_commands.guild_only()
async def ask_grammar_bot(interaction: discord.Interaction, message: discord.Message):
    # The target message's text is included in the interaction, so members can
    # keep posting questions normally and anyone can hand one to the bot.
    if message.channel.id not in channel_list:
        await interaction.response.send_message(
            "I only answer questions in the grammar channels.", ephemeral=True)
        return
    if not message.content.strip():
        await interaction.response.send_message("That message has no text to answer.", ephemeral=True)
        return
    if message.thread is not None or message.id in thread_message_count:
        await interaction.response.send_message("That question already has a thread.", ephemeral=True)
        return
    await interaction.response.send_message("On it!", ephemeral=True)
    thread = await message.create_thread(name=thread_name_for(message.content), auto_archive_duration=60)
    await answer_in_thread(thread, message.content)


async def recover_opening_question(thread):
    """The question behind a thread we lost track of (e.g. after a restart).

    Only recoverable for /grammar threads, whose starter is the bot's own
    message; a member's own starter message arrives without its text.
    """
    try:
        starter = await thread.parent.fetch_message(thread.id)
    except (discord.HTTPException, AttributeError):
        return None
    if starter.author == bot.user and ASKED_PREFIX in starter.content:
        return starter.content.split(ASKED_PREFIX, 1)[1]
    return None


async def is_addressed_to_bot(message):
    """True if a thread message mentions the bot or replies to one of its messages."""
    if bot.user in message.mentions:
        return True
    ref = message.reference
    if ref is None or ref.message_id is None:
        return False
    target = ref.resolved if isinstance(ref.resolved, discord.Message) else None
    if target is None:
        try:
            target = await message.channel.fetch_message(ref.message_id)
        except discord.HTTPException:
            return False
    return target.author == bot.user


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not (isinstance(message.channel, discord.Thread) and message.channel.parent_id in channel_list):
        return
    if not await is_addressed_to_bot(message):
        return

    # Without the Message Content intent we only get the text of messages that
    # mention the bot. A reply with "ping" turned off arrives empty.
    question = strip_bot_mention(message.content) if message.content else ''
    if not question:
        await message.channel.send(MENTION_NEEDED_MESSAGE)
        return

    thread_id = message.channel.id
    answers = thread_message_count.get(thread_id, 0)  # bot answers so far
    if answers > MAX_FOLLOWUPS + 1:
        return
    if answers == MAX_FOLLOWUPS + 1:
        await message.channel.send(LIMIT_MESSAGE)
        thread_message_count[thread_id] += 1
        return
    thread_message_count[thread_id] = answers + 1

    async with message.channel.typing():
        # Rebuild the conversation: the opening question, then the bot's
        # answers and the follow-ups that mention it (the only thread messages
        # whose text we receive), minus the bot's filler lines.
        history = []
        async for msg in message.channel.history(limit=12):
            if msg.author == bot.user:
                if msg.content and msg.content not in FILLER_MESSAGES:
                    history.insert(0, {"role": "assistant", "content": msg.content})
            elif msg.content and bot.user in msg.mentions:
                text = strip_bot_mention(msg.content)
                if text:
                    history.insert(0, {"role": "user", "content": text})
        opening = thread_questions.get(thread_id) or await recover_opening_question(message.channel)
        if opening:
            history.insert(0, {"role": "user", "content": opening})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        output = await get_completion(messages)
        if output:
            for chunk in split_message(output):
                await message.channel.send(chunk)
        else:
            await message.channel.send(ERROR_MESSAGE)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grammar bot')
    parser.add_argument('auth_key', type=str, help='the key to authenticate this discord bot with discord')
    args = parser.parse_args()

    bot.run(args.auth_key)
