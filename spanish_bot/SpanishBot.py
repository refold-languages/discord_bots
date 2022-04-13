from ast import alias
import discord
from discord.ext import commands
import pickle
import random
import doclist
import argparse

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(intents=intents, command_prefix='!')
#help_command = commands.DefaultHelpCommand(no_category = 'Commands')

@bot.event
async def on_ready():
  name = bot.user
  print(f'We have logged in as {name}')

@bot.event
async def on_command_error(ctx, error):
  print(str(error))
  await ctx.message.delete()

@bot.command(help='Checks the ping of the bot.', category='General Commands')
async def ping(ctx):
  await ctx.send(f'Pong! The bot\'s latency is {round(bot.latency * 1000)}ms')

#----- General Response Commands -----#

@bot.command(help='Hola?', category='General Commands')
async def hola(ctx):
  await ctx.send(f'Hola {ctx.author.mention}! :wave:')

@bot.command(help='Ayuda', category='General Commands')
async def ayuda(ctx):
  await ctx.send(f'Buenos días y bienvenido/a a Refold. Parece que tienes problemas uniéndote a un servidor. Dirígete a <#780906329811451944> y haz click en la bandera del Reino Unido para unirte al servidor de Refold English, para el aprendizaje de inglés. También te recomendamos hacer clic en la bandera de España para unirte al servidor de Refold Español (donde podrás no solo interactuar y ayudar a angloparlantes con su español, pero también recibir ayuda con tu inglés). Si necesitas más ayuda, menciona a @Spanish Helper.')

@bot.command(help='Remind people of rule one.', category='General Commands')
async def rule1(ctx, user=''):
  if user == '':
    await ctx.send(f'**1. Don\'t be an asshole**\n- No racism, sexism, homophobia, or religious attacks.\n- Treat each other with respect.\n- Text doesn\'t convey emotion. Assume the best in people.\n- No Nazis: no pro-nazi symbolism, profile pictures, or ideology. Please report these immediately to a moderator.')
  else:
    await ctx.send(f'Hey {user}, please remember Rule 4:\n**1. Don\'t be an asshole**\n- No racism, sexism, homophobia, or religious attacks.\n- Treat each other with respect.\n- Text doesn\'t convey emotion. Assume the best in people.\n- No Nazis: no pro-nazi symbolism, profile pictures, or ideology. Please report these immediately to a moderator.')

@bot.command(help='Remind people of rule two.', category='General Commands')
async def rule2(ctx, user=''):
  if user == '':
    await ctx.send(f'**2. Be welcoming and helpful to newcomers**\n- Don\'t yell at people for not reading the method. Instead, guide them to the relevant article.\n- When answering questions, give them enough to get started + additional resources they\'ll need.\n- Teach people how to fish. Don\'t just give them the fish.')
  else:
    await ctx.send(f'Hey {user}, please remember Rule 4:\n**2. Be welcoming and helpful to newcomers**\n- Don\'t yell at people for not reading the method. Instead, guide them to the relevant article.\n- When answering questions, give them enough to get started + additional resources they\'ll need.\n- Teach people how to fish. Don\'t just give them the fish.')

@bot.command(help='Remind people of rule three.', category='General Commands')
async def rule3(ctx, user=''):
  if user == '':
    await ctx.send(f'**3. Don\'t be a zealot**\n- No bashing other languages.\n- Refold is a method. Not a dogma. It\'s ok to deviate. HOWEVER, if you talk about those deviations in the chat, make it clear that they are your personal modifications and not part of the core method.\n- Debate and discussion about language learning is ok. No fighting.')
  else:
    await ctx.send(f'Hey {user}, please remember Rule 4:\n**3. Don\'t be a zealot**\n- No bashing other languages.\n- Refold is a method. Not a dogma. It\'s ok to deviate. HOWEVER, if you talk about those deviations in the chat, make it clear that they are your personal modifications and not part of the core method.\n- Debate and discussion about language learning is ok. No fighting.')

@bot.command(help='Remind people of rule four.', category='General Commands')
async def rule4(ctx, user=''):
  if user == '':
    await ctx.send(f'**4. Stay on Topic**\n- Language content only except for off-topic.\n- Keep content PG-13. No Adult Content.\n- No Spamming\n- No self-promotion.\n- No political debates.')
  else:
    await ctx.send(f'Hey {user}, please remember Rule 4:\n**4. Stay on Topic**\n- Language content only except for off-topic.\n- Keep content PG-13. No Adult Content.\n- No Spamming\n- No self-promotion.\n- No political debates.')

@bot.command(help='Remind people of the rules.', category='General Commands')
async def rules(ctx, user=''):
  if user == '':
    await ctx.send(f'**1. Don\'t be an asshole**\n- No racism, sexism, homophobia, or religious attacks.\n- Treat each other with respect.\n- Text doesn\'t convey emotion. Assume the best in people.\n- No Nazis: no pro-nazi symbolism, profile pictures, or ideology. Please report these immediately to a moderator.\n**2. Be welcoming and helpful to newcomers**\n- Don\'t yell at people for not reading the method. Instead, guide them to the relevant article.\n- When answering questions, give them enough to get started + additional resources they\'ll need.\n- Teach people how to fish. Don\'t just give them the fish.\n**3. Don\'t be a zealot**\n- No bashing other languages.\n- Refold is a method. Not a dogma. It\'s ok to deviate. HOWEVER, if you talk about those deviations in the chat, make it clear that they are your personal modifications and not part of the core method.\n- Debate and discussion about language learning is ok. No fighting.\n**4. Stay on Topic**\n- Language content only except for off-topic.\n- Keep content PG-13. No Adult Content.\n- No Spamming\n- No self-promotion.\n- No political debates.')
  else:
    await ctx.send(f'Hey {user}, please remember Rule 4:\n**1. Don\'t be an asshole**\n- No racism, sexism, homophobia, or religious attacks.\n- Treat each other with respect.\n- Text doesn\'t convey emotion. Assume the best in people.\n- No Nazis: no pro-nazi symbolism, profile pictures, or ideology. Please report these immediately to a moderator.\n**2. Be welcoming and helpful to newcomers**\n- Don\'t yell at people for not reading the method. Instead, guide them to the relevant article.\n- When answering questions, give them enough to get started + additional resources they\'ll need.\n- Teach people how to fish. Don\'t just give them the fish.\n**3. Don\'t be a zealot**\n- No bashing other languages.\n- Refold is a method. Not a dogma. It\'s ok to deviate. HOWEVER, if you talk about those deviations in the chat, make it clear that they are your personal modifications and not part of the core method.\n- Debate and discussion about language learning is ok. No fighting.\n**4. Stay on Topic**\n- Language content only except for off-topic.\n- Keep content PG-13. No Adult Content.\n- No Spamming\n- No self-promotion.\n- No political debates.')

@bot.command(help='Responds to frequently asked questions.', category='General Commands')
async def faq1(ctx):
  await ctx.send(f'**FAQ#1**:  Can you make a channel/category/server for my target language?\n\nChannels: Upon request, any language can get a role and a channel. Ask in server-feedback and we\'ll add it. New channels are added once per week in bulk.\n\nCategories: When a community grows, they can request a category, multiple channels, and a google doc for resources.\n\nServers: When a community has a dedicated admin and 25 active members, they can request a dedicated server.')

@bot.command(help='Responds to frequently asked questions.', category='General Commands')
async def faq2(ctx):
  await ctx.send(f'**FAQ#2**: Is there a server for X language?\nThere are currently servers for Japanese, Spanish, English, Korean, Russian, French, German, Mandarin, Cantonese, Portuguese, Italian, Arabic')

@bot.command(help='Responds to frequently asked questions.', category='General Commands')
async def faqs(ctx):
  await ctx.send(f'**FAQ#1**:  Can you make a channel/category/server for my target language?\n\nChannels: Upon request, any language can get a role and a channel. Ask in server-feedback and we\'ll add it. New channels are added once per week in bulk.\n\nCategories: When a community grows, they can request a category, multiple channels, and a google doc for resources.\n\nServers: When a community has a dedicated admin and 25 active members, they can request a dedicated server.\n\n**FAQ#2**: Is there a server for X language?\nThere are currently servers for Japanese, Spanish, English, Korean, Russian, French, German, Mandarin, Cantonese, Portuguese, Italian, Arabic')

#----- Auto Thread Channels -----#

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def setthreadchannel(ctx):
  channel = ctx.channel.id
  try:
    thread_channels = pickle.load(open('thread_channels.dat', 'rb'))
  except:
    thread_channels = [channel]
  if channel not in thread_channels:
    thread_channels.append(channel)
    pickle.dump(thread_channels, open('thread_channels.dat', 'wb'))
    await ctx.send('Done.')
  else:
    await ctx.send('This channel is already in my list!')

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def addthreadchannel(ctx, channel):
  channel = int(channel)
  try:
    thread_channels = pickle.load(open('thread_channels.dat', 'rb'))
  except:
    thread_channels = [channel]
  if channel not in thread_channels:
    thread_channels.append(channel)
    pickle.dump(thread_channels, open('thread_channels.dat', 'wb'))
    await ctx.send('Done.')
  else:
    await ctx.send('This channel is already in my list!')

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def printthreadchannels(ctx):
  try:
    thread_channels = pickle.load(open('thread_channels.dat', 'rb'))
    print(thread_channels)
  except:
    return
  
@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def removethreadchannel(ctx):
  channel = ctx.channel.id
  try:
    thread_channels = pickle.load(open('thread_channels.dat', 'rb'))
  except:
    await ctx.send('This channel isn\'t in my list.')
  if channel in thread_channels:
    thread_channels.remove(channel)
    pickle.dump(thread_channels, open('thread_channels.dat', 'wb'))
    await ctx.send('Done.')
  else:
    await ctx.send('This channel isn\'t in my list.')

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def clearthreadchannels(ctx):
  thread_channels = []
  pickle.dump(thread_channels, open('thread_channels.dat', 'wb'))
  await ctx.send('Channels cleared.')

@bot.listen('on_message')
async def on_message(message):
  thread_channels = pickle.load(open('thread_channels.dat', 'rb'))
  if message.channel.id in thread_channels and message.author != bot.user and not message.content.startswith(bot.command_prefix):
    title = str(message.content)
    title = title.split()[:5]
    title = str(" ".join(title)) + '...'
    await message.create_thread(name=str(title))
  else:
    return

#----- Randomizer Commands -----#

@bot.command(help='Roll a any number of dice with any number of sides')
async def roll(ctx, dice='1d20', mod='+0'):
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

@bot.command(help='Just flips a coin. Pretty easy.', aliases=['coinflip'])
async def flipacoin(ctx):
  options = ['Heads', 'Tails']
  coin = random.choice(options)
  await ctx.send(f'{ctx.author.mention}, the coin landed on **{coin}**!')

#----- Misc Commands -----#

@bot.command(help='Cheese', aliases=['cheese', 'mycheze', 'mycheezy'])
async def mycheesy(ctx):
  await ctx.send(':cheese:')

@bot.command(help='Bacon', aliases=['gorg', 'george', 'georgepag'])
async def gorgpag(ctx):
  await ctx.send(':bacon:')

#----- Doc Commands -----#

@bot.command(help='Show the Spanish Resource Doc link', aliases=['espdoc', 'spadoc'])
async def spanishdoc(ctx, target='False'):
  if target == 'False':
    await ctx.send(f'<http://refold.link/spanish>')
  else:
    await ctx.send(f'{target} <http://refold.link/spanish>')

@bot.command(hidden=True, aliases=['japanesedoc', 'japandoc'])
async def jpdoc(ctx):
  await ctx.send(f'{doclist.docjp}')
  
#----- April Update -----# 

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def createproject(ctx, name=None):
  if name is None:
    await ctx.send(f'Please give your project a name. Use `!createproject [projectname]`.')
  else:
    name = name.lower()
    try:
      projects = pickle.load(open('projects.dat', 'rb'))
    except:
      projects = []
    if name not in projects:
      projects.append(name)
      pickle.dump(projects, open('projects.dat', 'wb'))
      category_name = "COMMUNITY PROJECTS"
      await ctx.send("Setting up channel!")
      category = discord.utils.get(ctx.guild.categories, name=category_name)
      user = ctx.author.id
      overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False), 
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True), 
        ctx.author: discord.PermissionOverwrite(read_messages=True)
        }

      if category is None: #If there's no category matching with the `name`
        category = await ctx.guild.create_category(category_name, reason=None)
        channel = await ctx.guild.create_text_channel(name=name, overwrites=overwrites, reason=None, category=category)
        invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
        await ctx.author.send(invitelink)

      else: #Else if it found the category
        channel = await ctx.guild.create_text_channel(name=name, overwrites=overwrites, reason=None, category=category)
        invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
        await ctx.author.send(invitelink)
    else:
      await ctx.send('There\'s already a project with this name!')

@bot.command()
async def joinproject(ctx, name=None):
  if name is None:
    await ctx.send(f'Which project would you like to join? Please use `!joinproject [projectname]`.')
  else:
    name = name.lower()
    try:
      projects = pickle.load(open('projects.dat', 'rb'))
    except:
      await ctx.send(f'There are no open projects.')
    if name in projects:
      channel = discord.utils.get(ctx.guild.channels, name=name)
      overwrite = discord.PermissionOverwrite()
      overwrite.read_messages = True
      await channel.set_permissions(ctx.author, overwrite=overwrite)
      invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
      await ctx.author.send(invitelink)
    else:
      await ctx.send(f'There\'s no project with this name.')
    
@bot.command(hidden=True, aliases=['archiveproject'])
@commands.has_permissions(manage_channels=True)
async def endproject(ctx, name=None):
  if name is None:
    await ctx.send(f'Which project would you like to archive? Please use `!endproject [projectname]`.')
  else:
    name = name.lower()
    try:
      projects = pickle.load(open('projects.dat', 'rb'))
    except:
      await ctx.send(f'There are no open projects.')
    if name in projects:
      category = discord.utils.get(ctx.guild.categories, name='ARCHIVE')
      if category is None: #If there's no category matching with the `name`
        category = await ctx.guild.create_category('ARCHIVE', reason=None)
        channel = discord.utils.get(ctx.guild.channels, name=name)
        await channel.edit(category=category)
        await ctx.send(f'Project \'{name}\' has been moved to the archive.')
      else: #Else if it found the category
        channel = discord.utils.get(ctx.guild.channels, name=name)
        await channel.edit(category=category)
        await ctx.send(f'Project \'{name}\' has been moved to the archive.')
    else:
      await ctx.send(f'There\'s no project with this name.')

#----- Requested Commands -----#

@bot.command(aliases=['2L2', 'twol2', 'twoltwo', 'twoLtwo', '2l2'])
async def twoL2(ctx):
  await ctx.send(f'https://www.youtube.com/watch?v=PlteftANWoE')

@bot.command(aliases=['STAGE1', 'Stage1', 'StageOne', 'Stage_1'])
async def stage1(ctx):
  await ctx.send(f'Develop an immersion habit. Study some grammar, find a way to study vocabulary (memrise, quantized, anki etc. ), find content that is compelling and comprehensible ( things you have watched before, subjects that inherently interest you ). When you start sentence mining, you are stage 2a.')

@bot.command(aliases=['SentenceMine', 'sentence_mine', 'sentencemining', 'sentence_mining'])
async def sentencemine(ctx):
  await ctx.send(f'When you encounter a sentence where either one word is unknown, or you just don\’t understand the grammar. We call that 1T. This sentence may be recorded by making it a card on anki or a physical one. The point is that you are learning words most relevant to your immersion past the first 1k words.')

@bot.command(aliases=['shadow', 'languageparent', 'langparent'])
async def shadowing(ctx):
  await ctx.send(f'The point of this exercise is to practice imitating full native speed to get used to the sounds, rhythm and mannerisms of your language parent (the one you want to most speak like). You can find the article here, <https://refold.la/roadmap/stage-3/b/pronunciation-training>')

parser = argparse.ArgumentParser(description='Bot de español')
parser.add_argument('auth_key', type=str, help='the key to authenticate this discord bot with discord')
args = parser.parse_args()
bot.run(args.auth_key)
