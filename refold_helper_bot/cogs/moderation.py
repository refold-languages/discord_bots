"""
Moderation cog for Refold Helper Bot.
Handles rules, FAQs, message monitoring, and community guidelines.
"""

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config.constants import IGNORED_SERVER_IDS, DELETED_MESSAGE_LOG_CHANNEL_ID


RULES = [
    ('**1. Don\'t be an asshole**\n'
     '- No racism, sexism, homophobia, or religious attacks.\n'
     '- Treat each other with respect.\n'
     '- Text doesn\'t convey emotion. Assume the best in people.\n'
     '- No Nazis: no pro-nazi symbolism, profile pictures, or ideology. Please report these immediately to a moderator.'),
    ('**2. Be welcoming and helpful to newcomers**\n'
     '- Don\'t yell at people for not reading the method. Instead, guide them to the relevant article.\n'
     '- When answering questions, give them enough to get started + additional resources they\'ll need.\n'
     '- Teach people how to fish. Don\'t just give them the fish.'),
    ('**3. Don\'t be a zealot**\n'
     '- No bashing other languages.\n'
     '- Refold is a method. Not a dogma. It\'s ok to deviate. HOWEVER, if you talk about those deviations in the chat, make it clear that they are your personal modifications and not part of the core method.\n'
     '- Debate and discussion about language learning is ok. No fighting.'),
    ('**4. Stay on Topic**\n'
     '- Language content only except for off-topic.\n'
     '- Keep content PG-13. No Adult Content.\n'
     '- No Spamming\n'
     '- No self-promotion.\n'
     '- No political debates.'),
]

FAQS = [
    ('**FAQ#1**: Can you make a channel/category/server for my target language?\n\n'
     'Channels: Upon request, any language can get a role and a channel. Ask in server-feedback and we\'ll add it. New channels are added once per week in bulk.\n\n'
     'Categories: When a community grows, they can request a category, multiple channels, and a google doc for resources.\n\n'
     'Servers: When a community has a dedicated admin and 25 active members, they can request a dedicated server.'),
    ('**FAQ#2**: Is there a server for X language?\n'
     'There are currently servers for Japanese, Spanish, English, Korean, Russian, French, German, Mandarin, Cantonese, Portuguese, Italian, Arabic'),
]


class Moderation(commands.Cog):
    """Commands and events for community moderation and guidelines."""
    
    def __init__(self, bot):
        self.bot = bot

    # Rule commands
    @app_commands.command(description='Show the server rules, or remind someone of one.')
    @app_commands.describe(number='Which rule to show (default: all of them)',
                           user='Someone to remind about the rule')
    @app_commands.choices(number=[
        app_commands.Choice(name="All rules", value=0),
        app_commands.Choice(name="1. Don't be an asshole", value=1),
        app_commands.Choice(name="2. Be welcoming and helpful to newcomers", value=2),
        app_commands.Choice(name="3. Don't be a zealot", value=3),
        app_commands.Choice(name="4. Stay on Topic", value=4),
    ])
    async def rule(self, interaction: discord.Interaction,
                   number: Optional[app_commands.Choice[int]] = None,
                   user: Optional[discord.Member] = None):
        """Display a rule (or all rules), optionally addressed to a user."""
        rule_number = number.value if number else 0
        if rule_number:
            text = RULES[rule_number - 1]
            label = f'Rule {rule_number}'
        else:
            text = '\n'.join(RULES)
            label = 'the rules'

        if user is None:
            await interaction.response.send_message(text)
        else:
            await interaction.response.send_message(
                f'Hey {user.mention}, please remember {label}:\n{text}',
                allowed_mentions=discord.AllowedMentions(users=[user]))

    # FAQ commands
    @app_commands.command(description='Responds to frequently asked questions.')
    @app_commands.describe(topic='Which FAQ to show (default: all of them)')
    @app_commands.choices(topic=[
        app_commands.Choice(name='All FAQs', value=0),
        app_commands.Choice(name='1. Can you make a channel/category/server for my language?', value=1),
        app_commands.Choice(name='2. Is there a server for X language?', value=2),
    ])
    async def faq(self, interaction: discord.Interaction,
                  topic: Optional[app_commands.Choice[int]] = None):
        """Display one FAQ, or all of them."""
        faq_number = topic.value if topic else 0
        if faq_number:
            await interaction.response.send_message(FAQS[faq_number - 1])
        else:
            await interaction.response.send_message('\n\n'.join(FAQS))

    # Community greeting commands
    @app_commands.command(description='Hola?')
    async def hola(self, interaction: discord.Interaction):
        """Spanish greeting command."""
        await interaction.response.send_message(f'Hola {interaction.user.mention}! :wave:')

    @app_commands.command(description='Ayuda para unirse a un servidor')
    async def ayuda(self, interaction: discord.Interaction):
        """Spanish help message for server navigation."""
        await interaction.response.send_message(
            'Buenos días y bienvenido/a a Refold. Parece que tienes problemas uniéndote a un servidor. '
            'Dirígete a <#780906329811451944> y haz click en la bandera del Reino Unido para unirte al servidor de Refold English, para el aprendizaje de inglés. '
            'También te recomendamos hacer clic en la bandera de España para unirte al servidor de Refold Español '
            '(donde podrás no solo interactuar y ayudar a angloparlantes con su español, pero también recibir ayuda con tu inglés). '
            'Si necesitas más ayuda, menciona a @Spanish Helper.')

    # Event handlers
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log deleted messages to moderation channel."""
        if message.guild is None or message.guild.id in IGNORED_SERVER_IDS:
            return
        # Without the Message Content intent every message arrives with empty
        # content, and Discord rejects an embed field with an empty value -
        # there is nothing worth logging, so skip rather than 400 on each one.
        if not message.content:
            return

        embed = discord.Embed(
            title=f'A message was deleted in {message.guild.name}',
            description='',
            color=0x4287f5
        )
        # Embed field values are capped at 1024 characters.
        content = message.content if len(message.content) <= 1024 else message.content[:1021] + '...'
        embed.add_field(name='The deleted message is:', value=content, inline=True)
        embed.add_field(name='It was sent by:', value=f'{message.author.mention}', inline=True)
        
        channel = self.bot.get_channel(DELETED_MESSAGE_LOG_CHANNEL_ID)
        if channel:
            await channel.send('', embed=embed)


async def setup(bot):
    """Add the Moderation cog to the bot."""
    await bot.add_cog(Moderation(bot))