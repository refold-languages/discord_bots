"""
Fun commands cog for Refold Helper Bot.
Contains games, jokes, and interactive entertainment commands.
"""

import random
from discord.ext import commands


class Fun(commands.Cog):
    """Fun and interactive commands for community engagement."""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help='Roll any number of dice with any number of sides')
    async def roll(self, ctx, dice='1d20', mod='+0'):
        """Roll dice with optional modifier (e.g., !roll 2d6 +3)."""
        try:
            result = 0
            rolls = 0
            number = dice.split('d', 1)[0]
            sides = dice.split('d', 1)[1]
            modnum = mod[1:]
            modsign = mod[0]
            
            while rolls < int(number):
                rolls = rolls + 1
                result = result + random.randint(1, int(sides))
            
            if modsign == '+':
                result = result + int(modnum)
            else:
                result = result - int(modnum)
            
            if mod == '+0':
                await ctx.send(f'{ctx.author.mention}, you got a {str(result)}! You rolled {dice}.')
            else:
                await ctx.send(f'{ctx.author.mention}, you got a {str(result)}! You rolled {dice} and modified it with {mod}.')
                
        except (ValueError, IndexError):
            await ctx.send('Invalid dice format! Use format like: 1d20, 2d6+3, 3d8-1')

    @commands.command(help='Just flips a coin. Pretty easy.', aliases=['coinflip', 'flip'])
    async def flipacoin(self, ctx):
        """Flip a coin and get heads or tails."""
        options = ['Heads', 'Tails']
        coin = random.choice(options)
        await ctx.send(f'{ctx.author.mention}, the coin landed on **{coin}**!')

    @commands.command(help='Cheese', aliases=['cheese', 'mycheze', 'mycheezy'])
    async def mycheesy(self, ctx):
        """Community inside joke - cheese emoji."""
        await ctx.send(':cheese:')

    @commands.command(help='Bacon', aliases=['gorg', 'george', 'georgepag'])
    async def gorgpag(self, ctx):
        """Community inside joke - bacon emoji."""
        await ctx.send(':bacon:')


async def setup(bot):
    """Add the Fun cog to the bot."""
    await bot.add_cog(Fun(bot))