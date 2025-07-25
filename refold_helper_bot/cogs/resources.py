"""
Resources cog for Refold Helper Bot.
Handles video/doc lookup, educational content, and resource links.
"""

import csv
import discord
from discord.ext import commands

import doclist
from config.constants import VIDEO_LINKS_FILE, CROWDSOURCE_DOCS_FILE


class Resources(commands.Cog):
    """Commands for accessing learning resources and educational content."""
    
    def __init__(self, bot):
        self.bot = bot
        self.video_data = self._load_video_data()
        self.doc_data = self._load_docs_data()
    
    def _load_video_data(self):
        """Load video reference data from TSV file."""
        videos = []
        try:
            with open(VIDEO_LINKS_FILE, 'r') as file:
                reader = csv.DictReader(file, delimiter='\t', fieldnames=['title', 'references', 'link'])
                for row in reader:
                    row['references'] = row['references'].lower().split(', ')
                    videos.append(row)
        except FileNotFoundError:
            print(f"Warning: {VIDEO_LINKS_FILE} not found")
        return videos
    
    def _load_docs_data(self):
        """Load documentation reference data from TSV file."""
        docs = []
        try:
            with open(CROWDSOURCE_DOCS_FILE, 'r') as file:
                reader = csv.DictReader(file, delimiter='\t', fieldnames=['title', 'references', 'link'])
                for row in reader:
                    row['references'] = row['references'].lower().split(', ')
                    docs.append(row)
        except FileNotFoundError:
            print(f"Warning: {CROWDSOURCE_DOCS_FILE} not found")
        return docs
    
    def _find_video(self, query):
        """Find video by query in references."""
        query = query.lower()
        for video in self.video_data:
            if query in video['references']:
                return video['link']
        return "No video found for your query."
    
    def _find_doc(self, query):
        """Find documentation by query in references."""
        query = query.lower()
        for doc in self.doc_data:
            if query in doc['references']:
                return doc['link']
        return "No document found for your query."

    # Resource lookup commands
    @commands.command(name='video')
    async def video(self, ctx, *, query: str):
        """Search for instructional videos by keyword."""
        video_link = self._find_video(query)
        await ctx.send(video_link)

    @commands.command(name='doc', aliases=['crowdsourcedoc', 'resourcedoc'])
    async def doc(self, ctx, *, query: str):
        """Search for documentation by language or topic."""
        doc_link = self._find_doc(query)
        await ctx.send(doc_link)

    # Direct resource links
    @commands.command(hidden=True, aliases=['japanesedoc', 'japandoc'])
    async def jpdoc(self, ctx):
        """Get link to Japanese resources document."""
        await ctx.send(f'{doclist.docjp}')

    # Educational content commands
    @commands.command(aliases=['2L2', 'twol2', 'twoltwo', 'twoLtwo', '2l2'])
    async def twoL2(self, ctx):
        """Information about learning two languages simultaneously."""
        await ctx.send('Learning two languages at the same time is totally possible, but it\'s less efficient than doing one language and then the other. This is because you will lose some time switching between the languages, you\'re more likely to get confused, etc. For more information, watch this video: https://www.youtube.com/watch?v=PlteftANWoE')

    @commands.command(aliases=['STAGE1', 'Stage1', 'StageOne', 'Stage_1'])
    async def stage1(self, ctx):
        """Explanation of Refold Stage 1."""
        await ctx.send('Develop an immersion habit. Study some grammar, find a way to study vocabulary (memrise, quantized, anki etc. ), find content that is compelling and comprehensible ( things you have watched before, subjects that inherently interest you ). When you start sentence mining, you are stage 2a.')

    @commands.command(aliases=['SentenceMine', 'sentence_mine', 'sentencemining', 'sentence_mining'])
    async def sentencemine(self, ctx):
        """Explanation of sentence mining technique."""
        await ctx.send('When you encounter a sentence where either one word is unknown, or you just don\'t understand the grammar. We call that 1T. This sentence may be recorded by making it a card on anki or a physical one. The point is that you are learning words most relevant to your immersion past the first 1k words.')

    @commands.command(aliases=['shadow', 'languageparent', 'langparent'])
    async def shadowing(self, ctx):
        """Explanation of shadowing technique."""
        await ctx.send('The point of this exercise is to practice imitating full native speed to get used to the sounds, rhythm and mannerisms of your language parent (the one you want to most speak like). You can find the article here, <https://refold.la/roadmap/stage-3/b/pronunciation-training>')

    @commands.command(aliases=['homework', 'hwhelp', 'hw', 'helpwithhomework', 'homework-help'], 
                     help='Basic response to people asking for help with their homework', category='General Commands')
    async def homeworkhelp(self, ctx): 
        """Response for homework help requests."""
        await ctx.send('Hey! It looks like you\'re looking for help with your homework. Refold isn\'t the place to get homework help. We\'re a community of dedicated language learners and our primary focus is NOT on grammar exercises and translations.\n\nIf you don\'t really care about learning and just want help on your homework, DeepL + ChatGPT or another AI chatbot will be the best option. But please don\'t bother people with your homework questions. \n\nHowever, if you are actually interested in learning a language to a high level of fluency, we invite you to stick around! Here\'s a super short video explaining the Refold approach to language learning: https://youtu.be/GwDDirCcHos')

    # Utility commands
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def avatar(self, ctx, target: discord.Member = None):
        """Get avatar URL for a user."""
        if target is None:
            await ctx.send(f'{ctx.author.avatar}')
        else:
            await ctx.send(f'{target.avatar}')


async def setup(bot):
    """Add the Resources cog to the bot."""
    await bot.add_cog(Resources(bot))