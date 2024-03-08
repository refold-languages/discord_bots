import discord
from discord.ext import commands
from openai import OpenAI
import argparse

with open('openaiapi.txt', 'r') as token_file:
    openai_key = token_file.read().strip()\

openai_client = OpenAI(api_key=openai_key)

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(intents=intents, command_prefix='+')

channel_list = [1210371437802561637, 1215710869531656192]
thread_message_count = {}

@bot.event
async def on_ready():
    name = bot.user
    print(f'We have logged in as {name}')

@bot.command(help='Checks the ping of the bot.', category='General Commands')
async def ping(ctx):
    await ctx.send(f'Pong! The bot\'s latency is {round(bot.latency * 1000)}ms')

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    
    if message.author == bot.user or message.content.startswith('+'):
        return

    if message.channel.id in channel_list:
        thread_name = ' '.join(message.content.split()[:5])[:100]
        thread = await message.create_thread(name=thread_name, auto_archive_duration=60)
        thread_message_count[thread.id] = 1
        await thread.send("Allow me a moment to think.")
        async with thread.typing():
            customgpt = ("You are a specially trained GPT. Here is your training:\n"
                         "Role and Goal: Grammar Buddy is designed to assist immersion language learners by elucidating "
                         "grammar concepts in their target language. It specializes in breaking down grammatical rules into "
                         "understandable chunks, focusing exclusively on comprehension. Grammar Buddy explains what grammatical "
                         "constructions mean using natural language, practical examples, and simple words in the target language "
                         "to aid understanding.\n\nConstraints: It avoids drills, complex charts, obtuse grammar terms, and "
                         "detailed discussions on the creation or application of grammar patterns. The GPT is programmed not to "
                         "instruct users on how to use grammar patterns for language improvement but to ensure they grasp the "
                         "underlying concepts.\n\nGuidelines: When providing explanations, it heavily relies on examples in the "
                         "target language, using simple and accessible vocabulary. This approach helps learners intuitively "
                         "understand how grammar works in practical contexts. Official grammar terms are introduced sparingly, "
                         "and only to offer users paths for further exploration.\n\nClarification: If clarification is needed "
                         "to provide accurate help, it is ready to ask for more details.\n\nPersonalization: The GPT maintains "
                         "a supportive and encouraging tone, making grammar learning a less intimidating experience. It's tailored "
                         "to make grammar approachable, using examples that resonate with learners at all levels.\n"
                         "If a user asks a non language related question, respond with *Sorry, I can\'t answer that question.*")
            prompt = message.content
            response = openai_client.chat.completions.create(
                model="gpt-4-0125-preview",
                messages=[
                    {"role": "user", "content": customgpt},
                    {"role": "user", "content": prompt}
                ]
            )
            if response.choices and response.choices[0].message:
                output = response.choices[0].message.content
                await thread.send(output)
            else:
                await thread.send("Something went wrong. Please try again.")

    elif isinstance(message.channel, discord.Thread) and message.channel.parent_id in channel_list:
        thread_id = message.channel.id
        if thread_message_count.get(thread_id, 0) < 3:
            thread_message_count[thread_id] = thread_message_count.get(thread_id, 0) + 1
            await message.channel.send("Allow me a moment to think.")
            async with message.channel.typing():
                messages = []
                async for msg in message.channel.history(limit=5):
                    messages.insert(0, {"role": "user" if msg.author == message.author else "assistant", "content": msg.content})

                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                )
                if response.choices and response.choices[0].message:
                    output = response.choices[0].message.content
                    await message.channel.send(output)
        else:
            if thread_message_count.get(thread_id, 0) == 3:
                await message.channel.send("This conversation has reached its limit. Please open a new thread to continue.")
                thread_message_count[thread_id] += 1    

parser = argparse.ArgumentParser(description='Grammar bot')
parser.add_argument('auth_key', type=str, help='the key to authenticate this discord bot with discord')
args = parser.parse_args()

bot.run(args.auth_key)