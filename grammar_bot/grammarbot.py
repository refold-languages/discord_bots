import discord
from discord.ext import commands
from openai import OpenAI
import argparse
import asyncio

with open('deepseekapi.txt', 'r') as token_file:
    deepseek_key = token_file.read().strip()

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
FILLER_MESSAGES = {THINKING_MESSAGE, LIMIT_MESSAGE, ERROR_MESSAGE}

# Cap on the number of threads we track so the counter dict can't grow forever.
MAX_TRACKED_THREADS = 1000

intents = discord.Intents.all()
bot = commands.Bot(intents=intents, command_prefix='+')

channel_list = [1210371437802561637, 1215710869531656192, 1221944946827722832, 1221947610638581924]
thread_message_count = {}

@bot.event
async def on_ready():
    name = bot.user
    print(f'We have logged in as {name}')

@bot.command(help='Checks the ping of the bot.', category='General Commands')
async def ping(ctx):
    await ctx.send(f'Pong! The bot\'s latency is {round(bot.latency * 1000)}ms')

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

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author == bot.user or message.content.startswith('+') or message.content.startswith('!'):
        return

    if message.channel.id in channel_list:
        thread_name = ' '.join(message.content.split()[:5])[:100]
        thread = await message.create_thread(name=thread_name, auto_archive_duration=60)

        # Bound the tracking dict: evict the oldest entry once we're over the cap.
        if len(thread_message_count) >= MAX_TRACKED_THREADS:
            oldest = next(iter(thread_message_count))
            del thread_message_count[oldest]
        thread_message_count[thread.id] = 1
        await thread.send(THINKING_MESSAGE)

        async with thread.typing():
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message.content},
            ]
            output = await get_completion(messages)
            if output:
                for chunk in split_message(output):
                    await thread.send(chunk)
            else:
                await thread.send(ERROR_MESSAGE)

    elif isinstance(message.channel, discord.Thread) and message.channel.parent_id in channel_list:
        thread_id = message.channel.id
        if thread_message_count.get(thread_id, 0) < 3:
            thread_message_count[thread_id] = thread_message_count.get(thread_id, 0) + 1
            async with message.channel.typing():
                # Rebuild the conversation, dropping the bot's own filler lines,
                # then prepend the system prompt so the persona carries over.
                history = []
                async for msg in message.channel.history(limit=6):
                    if msg.author == bot.user and msg.content in FILLER_MESSAGES:
                        continue
                    role = "assistant" if msg.author == bot.user else "user"
                    history.insert(0, {"role": role, "content": msg.content})
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

                output = await get_completion(messages)
                if output:
                    for chunk in split_message(output):
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(ERROR_MESSAGE)
        else:
            if thread_message_count.get(thread_id, 0) == 3:
                await message.channel.send(LIMIT_MESSAGE)
                thread_message_count[thread_id] += 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Grammar bot')
    parser.add_argument('auth_key', type=str, help='the key to authenticate this discord bot with discord')
    args = parser.parse_args()

    bot.run(args.auth_key)
