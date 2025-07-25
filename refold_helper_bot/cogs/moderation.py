"""
Moderation cog for Refold Helper Bot.
Handles rules, FAQs, message monitoring, and community guidelines.
"""

import discord
from discord.ext import commands

from config.constants import IGNORED_SERVER_IDS, DELETED_MESSAGE_LOG_CHANNEL_ID


class Moderation(commands.Cog):
    """Commands and events for community moderation and guidelines."""
    
    def __init__(self, bot):
        self.bot = bot

    # Rule commands
    @commands.command(help='Remind people of rule one.', category='General Commands')
    async def rule1(self, ctx, user=''):
        """Display or remind someone about Rule 1."""
        rule_text = ('**1. Don\'t be an asshole**\n'
                    '- No racism, sexism, homophobia, or religious attacks.\n'
                    '- Treat each other with respect.\n'
                    '- Text doesn\'t convey emotion. Assume the best in people.\n'
                    '- No Nazis: no pro-nazi symbolism, profile pictures, or ideology. Please report these immediately to a moderator.')
        
        if user == '':
            await ctx.send(rule_text)
        else:
            await ctx.send(f'Hey {user}, please remember Rule 1:\n{rule_text}')

    @commands.command(help='Remind people of rule two.', category='General Commands')
    async def rule2(self, ctx, user=''):
        """Display or remind someone about Rule 2."""
        rule_text = ('**2. Be welcoming and helpful to newcomers**\n'
                    '- Don\'t yell at people for not reading the method. Instead, guide them to the relevant article.\n'
                    '- When answering questions, give them enough to get started + additional resources they\'ll need.\n'
                    '- Teach people how to fish. Don\'t just give them the fish.')
        
        if user == '':
            await ctx.send(rule_text)
        else:
            await ctx.send(f'Hey {user}, please remember Rule 2:\n{rule_text}')

    @commands.command(help='Remind people of rule three.', category='General Commands')
    async def rule3(self, ctx, user=''):
        """Display or remind someone about Rule 3."""
        rule_text = ('**3. Don\'t be a zealot**\n'
                    '- No bashing other languages.\n'
                    '- Refold is a method. Not a dogma. It\'s ok to deviate. HOWEVER, if you talk about those deviations in the chat, make it clear that they are your personal modifications and not part of the core method.\n'
                    '- Debate and discussion about language learning is ok. No fighting.')
        
        if user == '':
            await ctx.send(rule_text)
        else:
            await ctx.send(f'Hey {user}, please remember Rule 3:\n{rule_text}')

    @commands.command(help='Remind people of rule four.', category='General Commands')
    async def rule4(self, ctx, user=''):
        """Display or remind someone about Rule 4."""
        rule_text = ('**4. Stay on Topic**\n'
                    '- Language content only except for off-topic.\n'
                    '- Keep content PG-13. No Adult Content.\n'
                    '- No Spamming\n'
                    '- No self-promotion.\n'
                    '- No political debates.')
        
        if user == '':
            await ctx.send(rule_text)
        else:
            await ctx.send(f'Hey {user}, please remember Rule 4:\n{rule_text}')

    @commands.command(help='Remind people of the rules.', category='General Commands')
    async def rules(self, ctx, user=''):
        """Display all rules or remind someone about all rules."""
        all_rules = ('**1. Don\'t be an asshole**\n'
                    '- No racism, sexism, homophobia, or religious attacks.\n'
                    '- Treat each other with respect.\n'
                    '- Text doesn\'t convey emotion. Assume the best in people.\n'
                    '- No Nazis: no pro-nazi symbolism, profile pictures, or ideology. Please report these immediately to a moderator.\n'
                    '**2. Be welcoming and helpful to newcomers**\n'
                    '- Don\'t yell at people for not reading the method. Instead, guide them to the relevant article.\n'
                    '- When answering questions, give them enough to get started + additional resources they\'ll need.\n'
                    '- Teach people how to fish. Don\'t just give them the fish.\n'
                    '**3. Don\'t be a zealot**\n'
                    '- No bashing other languages.\n'
                    '- Refold is a method. Not a dogma. It\'s ok to deviate. HOWEVER, if you talk about those deviations in the chat, make it clear that they are your personal modifications and not part of the core method.\n'
                    '- Debate and discussion about language learning is ok. No fighting.\n'
                    '**4. Stay on Topic**\n'
                    '- Language content only except for off-topic.\n'
                    '- Keep content PG-13. No Adult Content.\n'
                    '- No Spamming\n'
                    '- No self-promotion.\n'
                    '- No political debates.')
        
        if user == '':
            await ctx.send(all_rules)
        else:
            await ctx.send(f'Hey {user}, please remember the rules:\n{all_rules}')

    # FAQ commands
    @commands.command(help='Responds to frequently asked questions.', category='General Commands')
    async def faq1(self, ctx):
        """FAQ about creating channels/categories/servers for languages."""
        await ctx.send('**FAQ#1**: Can you make a channel/category/server for my target language?\n\n'
                      'Channels: Upon request, any language can get a role and a channel. Ask in server-feedback and we\'ll add it. New channels are added once per week in bulk.\n\n'
                      'Categories: When a community grows, they can request a category, multiple channels, and a google doc for resources.\n\n'
                      'Servers: When a community has a dedicated admin and 25 active members, they can request a dedicated server.')

    @commands.command(help='Responds to frequently asked questions.', category='General Commands')
    async def faq2(self, ctx):
        """FAQ about available language servers."""
        await ctx.send('**FAQ#2**: Is there a server for X language?\n'
                      'There are currently servers for Japanese, Spanish, English, Korean, Russian, French, German, Mandarin, Cantonese, Portuguese, Italian, Arabic')

    @commands.command(help='Responds to frequently asked questions.', category='General Commands')
    async def faqs(self, ctx):
        """Display all FAQs."""
        await ctx.send('**FAQ#1**: Can you make a channel/category/server for my target language?\n\n'
                      'Channels: Upon request, any language can get a role and a channel. Ask in server-feedback and we\'ll add it. New channels are added once per week in bulk.\n\n'
                      'Categories: When a community grows, they can request a category, multiple channels, and a google doc for resources.\n\n'
                      'Servers: When a community has a dedicated admin and 25 active members, they can request a dedicated server.\n\n'
                      '**FAQ#2**: Is there a server for X language?\n'
                      'There are currently servers for Japanese, Spanish, English, Korean, Russian, French, German, Mandarin, Cantonese, Portuguese, Italian, Arabic')

    # Community greeting commands
    @commands.command(help='Hola?', category='General Commands')
    async def hola(self, ctx):
        """Spanish greeting command."""
        await ctx.send(f'Hola {ctx.author.mention}! :wave:')

    @commands.command(help='Ayuda', category='General Commands')
    async def ayuda(self, ctx):
        """Spanish help message for server navigation."""
        await ctx.send('Buenos días y bienvenido/a a Refold. Parece que tienes problemas uniéndote a un servidor. '
                      'Dirígete a <#780906329811451944> y haz click en la bandera del Reino Unido para unirte al servidor de Refold English, para el aprendizaje de inglés. '
                      'También te recomendamos hacer clic en la bandera de España para unirte al servidor de Refold Español '
                      '(donde podrás no solo interactuar y ayudar a angloparlantes con su español, pero también recibir ayuda con tu inglés). '
                      'Si necesitas más ayuda, menciona a @Spanish Helper.')

    # Event handlers
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log deleted messages to moderation channel."""
        if message.guild.id in IGNORED_SERVER_IDS:
            return 
        
        embed = discord.Embed(
            title=f'A message was deleted in {message.guild.name}', 
            description='', 
            color=0x4287f5
        )
        embed.add_field(name='The deleted message is:', value=f'{message.content}', inline=True)
        embed.add_field(name='It was sent by:', value=f'{message.author.mention}', inline=True)
        
        channel = self.bot.get_channel(DELETED_MESSAGE_LOG_CHANNEL_ID)
        if channel:
            await channel.send('', embed=embed)


async def setup(bot):
    """Add the Moderation cog to the bot."""
    await bot.add_cog(Moderation(bot))