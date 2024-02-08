from ast import alias
import discord
from discord.ext import commands
import pickle
import random
import doclist
import argparse
import json
import os
from os import path
import csv

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(intents=intents, command_prefix='!')
#help_command = commands.DefaultHelpCommand(no_category = 'Commands')

#----- Sub server role adding -----#

MAIN_SERVER_ID = 775877387426332682
ROLE_MAPPING = {
  778787713012727809: '775883964266840066', # Japanese
  667734565309382657: '780905794001698836', # Spanish
  778788342929031188: '780905858715615262', # Korean
  785938955823480842: '780978573514637332', # German
  784482683282915389: '780906072457347083', # Mandarin
  784471610270810166: '780978638421098508', # French
  784470147930783835: '780978715920171031', # English
  785922884446191649: '780978614409101362', # Russian
  833885350584778804: '784613059100278834', # Portuguese
  833879263823396864: '780979018957848596', # Italian
  856910581088780309: '780978677495627786', # Arabic
  789554739553632287: '784529021420568597', # Cantonese
  1030979301362900992: '804928731025899541', # Tagalog
}

async def assign_role_to_member(member, role_id):
  main_guild = await bot.fetch_guild(MAIN_SERVER_ID)
  if main_guild:
    roles = await main_guild.fetch_roles()
    role = discord.utils.find(lambda r: r.id == int(role_id), roles)
    if role:
      try:
        member_in_main_guild = await main_guild.fetch_member(member.id)
        await member_in_main_guild.add_roles(role)
      except discord.HTTPException:
        pass

async def remove_role_from_member(member, role_id):
  main_guild = await bot.fetch_guild(MAIN_SERVER_ID)
  if main_guild:
    roles = await main_guild.fetch_roles()
    role = discord.utils.find(lambda r: r.id == int(role_id), roles)
    if role:
      try:
        member_in_main_guild = await main_guild.fetch_member(member.id)
        await member_in_main_guild.remove_roles(role)
      except discord.HTTPException:
        pass

@bot.event
async def on_member_join(member):
    if member.guild.id != MAIN_SERVER_ID and member.guild.id in ROLE_MAPPING:
        role_id = ROLE_MAPPING[member.guild.id]
        await assign_role_to_member(member, role_id)

@bot.event
async def on_member_remove(member):
    if member.guild.id != MAIN_SERVER_ID and member.guild.id in ROLE_MAPPING:
        role_id = ROLE_MAPPING[member.guild.id]
        await remove_role_from_member(member, role_id)

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

@bot.event
async def on_message_delete(message):
    ignored_server_ids = [757802790532677683, 778787713012727809, 778331995297808438]
    if message.guild.id in ignored_server_ids:
      return 
    embed = discord.Embed(title=f'A message was deleted in {message.guild.name}', description='', color=0x4287f5)
    embed.add_field(name='The deleted message is:', value=f'{message.content}', inline=True)
    embed.add_field(name='It was sent by:', value=f'{message.author.mention}', inline=True)
    channel = bot.get_channel(966080907477909514)
    await channel.send('', embed=embed)

def read_language_roles():
    with open('language_roles.tsv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='\t')
        return {rows[0]: int(rows[1]) for rows in reader}

@bot.event
async def on_raw_reaction_add(payload):
  user = await bot.fetch_user(payload.user_id)
  guild = await bot.fetch_guild(payload.guild_id)
  member = await guild.fetch_member(payload.user_id)
  channel = await bot.fetch_channel(payload.channel_id)
  message = await channel.fetch_message(payload.message_id)
  emoji = str(payload.emoji)
  if emoji == '🔖':
    server = await bot.fetch_guild(payload.guild_id)
    embed = discord.Embed(title = f'You made a bookmark!', description='', color=0xc91f16)
    embed.add_field(name = 'The message said:', value = f'{message.content}', inline = True)
    msg = await user.send(f'Click to view original message: https://discord.com/channels/{server.id}/{channel.id}/{message.id}', embed=embed)
    await msg.add_reaction('❌')
  if emoji == '❌' and user != bot.user and message.author == bot.user:
    await message.delete()
  if payload.channel_id == 1202719368237293648 or payload.channel_id == 934209764819361902:  # Check if the reaction is in the specified channel
    server = await bot.fetch_guild(payload.guild_id)
    language_roles = read_language_roles()
    # Check if the emoji is in the TSV file and assign the role
    if emoji in language_roles:
      role_id = language_roles[emoji]
      role = server.get_role(role_id)
      if role:
        await member.add_roles(role)
    else:
      # If the emoji is not in the list, remove the reaction
      await message.remove_reaction(emoji, user)

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.channel_id == 1202719368237293648 or payload.channel_id == 934209764819361902:  # Check if the reaction is in the specified channel
        guild = await bot.fetch_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)  # Fetch the member
        emoji = str(payload.emoji)
        language_roles = read_language_roles()
        if emoji in language_roles:
            role_id = language_roles[emoji]
            role = guild.get_role(role_id)
            if role:
                await member.remove_roles(role)  # Remove the role from the member

def load_video_data(filename):
    videos = []
    with open(filename, 'r') as file:
        reader = csv.DictReader(file, delimiter='\t', fieldnames=['title', 'references', 'link'])
        for row in reader:
            row['references'] = row['references'].lower().split(', ')
            videos.append(row)
    return videos

# Load the data at the start of your bot
video_data = load_video_data('video_links.tsv')

def find_video(query, video_data):
    query = query.lower()
    for video in video_data:
        if query in video['references']:
            return video['link']
    return "No video found for your query."

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

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def setpollchannel(ctx):
  channel = ctx.channel.id
  try:
    poll_channels = pickle.load(open('poll_channels.dat', 'rb'))
  except:
    poll_channels = []
  if channel not in poll_channels:
    poll_channels.append(channel)
    pickle.dump(poll_channels, open('poll_channels.dat', 'wb'))
    await ctx.send('Done.')
  else:
    await ctx.send('This channel is already in my list!')

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def removepollchannel(ctx):
  channel = ctx.channel.id
  try:
    poll_channels = pickle.load(open('poll_channels.dat', 'rb'))
  except:
    await ctx.send('This channel isn\'t in my list.')
  if channel in poll_channels:
    poll_channels.remove(channel)
    pickle.dump(poll_channels, open('poll_channels.dat', 'wb'))
    await ctx.send('Done.')
  else:
    await ctx.send('This channel isn\'t in my list.')

@bot.listen('on_message')
async def on_message(message):
  if message.author != bot.user and not message.content.startswith(bot.command_prefix):
    thread_channels = pickle.load(open('thread_channels.dat', 'rb'))
    poll_channels = pickle.load(open('poll_channels.dat', 'rb'))
    if message.channel.id in thread_channels:
      title = str(message.content)
      title = title.split()[:5]
      title = str(" ".join(title)) + '...'
      await message.create_thread(name=str(title))
    elif message.channel.id in poll_channels:
      await message.add_reaction('<:ReUpvote:993947837836558417>')
      await message.add_reaction('<:ReDownvote:993947836796383333>')

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

@bot.command(help='Just flips a coin. Pretty easy.', aliases=['coinflip', 'flip'])
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
    await ctx.send(f'<https://refold.link/spanish_resources>')
  else:
    await ctx.send(f'{target} <https://refold.link/spanish_resources>')

@bot.command(hidden=True, aliases=['japanesedoc', 'japandoc'])
async def jpdoc(ctx):
  await ctx.send(f'{doclist.docjp}')
  
#----- Community Projects -----# 

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def json_migrate(ctx):
  projects = pickle.load(open('projects.dat', 'rb'))
  dict = {}
  for i in projects:
    dict[i] = ['description', 'leader']
  with open('projects.json', 'w') as file:
    json.dump(dict , file)

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def editproject(ctx, project, leader, description):
  with open('projects.json') as file:
    project_list = json.load(file)
  project_list[project] = [leader, description]
  with open('projects.json', 'w') as file:
    json.dump(project_list , file)

@bot.command(hidden=True)
async def listprojects(ctx):
  with open('projects.json') as file:
    project_list = json.load(file)
  embed = discord.Embed(title = 'The current projects are:', description='', color= 0x8566FF)
  for i in project_list:
    embed.add_field(name = i, value = f'*Leader*: {project_list[i][0]} \n*Description*: {project_list[i][1]}', inline=False)
  await ctx.send('', embed=embed)

@bot.command(hidden=True)
@commands.has_permissions(manage_channels=True)
async def createproject(ctx, name=None, leader=None, description=None):
  if name is None:
    await ctx.send(f'Please give your project a name. Use `!createproject [projectname] [] "[]"`.')
  elif leader is None:
    await ctx.send(f'Please give your project a leader. Use `!createproject [projectname] [] "[]"`.')
  elif description is None:
    await ctx.send(f'Please give your project a description. Use `!createproject [projectname] [] "[]"`.')
  else:
    name = name.lower()
    if path.exists('projects.json'):
      with open('projects.json') as file:
        projects = json.load(file)
    else:
      projects = {}
    if name not in projects:
      projects[name] = [leader, description]
      with open('projects.json', 'w') as file:
        json.dump(projects , file)
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
        await ctx.author.send(f'Here\'s a link to the project channel! Just in case your channel list is super long.\n{invitelink}')
    else:
      await ctx.send('There\'s already a project with this name!')

@bot.command()
async def joinproject(ctx, name=None):
  if name is None:
    await ctx.send(f'Which project would you like to join? Please use `!joinproject [projectname]`.')
  else:
    name = name.lower()
    if path.exists('projects.json'):
      with open('projects.json') as file:
        projects = json.load(file)
    else:
      await ctx.send(f'There are no open projects.')
    if name in projects:
      channel = discord.utils.get(ctx.guild.channels, name=name)
      overwrite = discord.PermissionOverwrite()
      overwrite.read_messages = True
      await channel.set_permissions(ctx.author, overwrite=overwrite)
      invitelink = await channel.create_invite(max_uses=1, unique=True, max_age=120)
      await ctx.author.send(f'If you\'re lost in the sauce, here\'s a link directly to the channel! Just in case it\'s hidden on your channel list.\n{invitelink}')
    else:
      await ctx.send(f'There\'s no project with this name.')
    
@bot.command(hidden=True, aliases=['archiveproject'])
@commands.has_permissions(manage_channels=True)
async def endproject(ctx, name=None):
  if name is None:
    await ctx.send(f'Which project would you like to archive? Please use `!endproject [projectname]`.')
  else:
    name = name.lower()
    if path.exists('projects.json'):
      with open('projects.json') as file:
        projects = json.load(file)
    else:
      await ctx.send(f'There are no open projects.')
    if name in projects:
      category = discord.utils.get(ctx.guild.categories, name='ARCHIVE')
      if category is None: #If there's no category matching with the `name`
        category = await ctx.guild.create_category('ARCHIVE', reason=None)
        channel = discord.utils.get(ctx.guild.channels, name=name)
        await channel.edit(category=category)
      else: #Else if it found the category
        channel = discord.utils.get(ctx.guild.channels, name=name)
        await channel.edit(category=category)
      del projects[name]
      with open('projects.json', 'w') as file:
        json.dump(projects , file)
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

@bot.command()
@commands.has_permissions(manage_channels=True)
async def avatar(ctx, target:discord.Member=None):
  if target is None:
    await ctx.send(f'{ctx.author.avatar}')
  else:
    await ctx.send(f'{target.avatar}')

#----- Video Commands -----#

@bot.command(name='video')
async def video(ctx, *, query: str):
    video_link = find_video(query, video_data)
    await ctx.send(video_link)

parser = argparse.ArgumentParser(description='Bot de español')
parser.add_argument('auth_key', type=str, help='the key to authenticate this discord bot with discord')
args = parser.parse_args()
bot.run(args.auth_key)
