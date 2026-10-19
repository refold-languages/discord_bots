"""
Fun commands cog for Refold Helper Bot.
Contains games, jokes, and interactive entertainment commands.
"""

import random

import discord
from discord import app_commands
from discord.ext import commands


class Fun(commands.Cog):
    """Fun and interactive commands for community engagement."""
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description='Roll any number of dice with any number of sides')
    @app_commands.describe(dice='Dice to roll, e.g. 1d20 or 2d6', mod='Modifier, e.g. +3 or -1')
    async def roll(self, interaction: discord.Interaction, dice: str = '1d20', mod: str = '+0'):
        """Roll dice with optional modifier (e.g., /roll 2d6 +3)."""
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
                await interaction.response.send_message(f'{interaction.user.mention}, you got a {str(result)}! You rolled {dice}.')
            else:
                await interaction.response.send_message(f'{interaction.user.mention}, you got a {str(result)}! You rolled {dice} and modified it with {mod}.')
                
        except (ValueError, IndexError):
            await interaction.response.send_message('Invalid dice format! Use format like: 1d20, 2d6 with mod +3, 3d8 with mod -1',
                                                    ephemeral=True)

    @app_commands.command(name='flipacoin', description='Just flips a coin. Pretty easy.')
    async def flipacoin(self, interaction: discord.Interaction):
        """Flip a coin and get heads or tails."""
        options = ['Heads', 'Tails']
        coin = random.choice(options)
        await interaction.response.send_message(f'{interaction.user.mention}, the coin landed on **{coin}**!')

    @app_commands.command(description='Cheese')
    async def mycheesy(self, interaction: discord.Interaction):
        """Community inside joke - cheese emoji."""
        await interaction.response.send_message(':cheese:')

    @app_commands.command(description='Bacon')
    async def gorgpag(self, interaction: discord.Interaction):
        """Community inside joke - bacon emoji."""
        await interaction.response.send_message(':bacon:')


async def setup(bot):
    """Add the Fun cog to the bot."""
    await bot.add_cog(Fun(bot))