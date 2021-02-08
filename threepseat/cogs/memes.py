import discord
import random
import re

from discord.ext import commands

from threepseat.constants import POG_RE, POG_EMOTE_RE, POG_EMOTES, DAD_RE


class Memes(commands.Cog):
    """Extension for Memes"""
    def __init__(self,
                 bot: commands.bot,
                 pog_reply: bool = False,
                 dad_reply: bool = False
        ) -> None:
        self.bot = bot
        self.pog_reply = pog_reply
        self.dad_reply = dad_reply


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Called when message is created and sent"""
        await self.replies(message)


    @commands.command(pass_context=True, brief='should I snowball?')
    async def snowball(self, ctx: commands.Context) -> None:
        """Command for taking a snowball"""
        msg = '{}, you should always take the snowball'.format(
              ctx.message.author.mention)
        await self.bot.message_guild(msg, ctx.channel)


    @commands.command(pass_context=True, brief='what are the odds? [max_num]')
    async def odds(self, ctx: commands.Context, num: int) -> None:
        """Command that returns random int in [1, num]"""
        rand = random.randint(1, num)
        await self.bot.message_guild('{}'.format(rand), ctx.channel)


    @commands.command(pass_context=True, brief='Flip a coin')
    async def flip(self, ctx: commands.Context) -> None:
        """Command that flips a coin"""
        rand = random.randint(1, 2)
        msg = 'heads' if rand == 1 else 'tails'
        await self.bot.message_guild('{}'.format(msg), ctx.channel)


    async def replies(self, message: discord.Message) -> None:
        """Process and handle meme replies to messages"""
        if self.pog_reply:
            text = message.content.lower()
            if re.search(POG_RE, text) or re.search(POG_EMOTE_RE, text):
                await self.bot.message_guild('poggers', message.channel,
                        POG_EMOTES)

        if self.dad_reply:
            search = re.findall(DAD_RE, text)
            if len(search) > 0:
                search = search[0]
                await self.bot.message_guild(
                        'Hi {}, I\'m {}!'.format(search[4], self.bot.user.mention),
                        message.channel)