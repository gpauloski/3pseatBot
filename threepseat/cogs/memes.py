"""Cog for random memes and commands"""
import discord
import random
import re

from discord.ext import commands

from threepseat.bot import Bot


POG_EMOTES = ['\U0001F1F5', '\U0001F1F4', '\U0001F1EC']
POG_RE = r'(p+\s*)+(o+\s*)+(g+\s*)+'
POG_EMOTE_RE = r'<:.*pog.*:\d*>'
DAD_RE = r'(^| |\n)((i\'?m)|(i am)) (\w+)'


class Memes(commands.Cog):
    """Extension for Memes

    Adds the following commands:
      - `?flip`: flips a coin
      - `?odds [num]`: give random integer in [1, number]
      - `?snowball`: should you take the snowball?
    """
    def __init__(
        self,
        bot: Bot,
        pog_reply: bool = False,
        dad_reply: bool = False
    ) -> None:
        """Init Memes

        Args:
            bot (Bot): bot that loaded this cog
            pog_reply (bool): if `True`, any message with some variation of
                pog in it will be replied to by the bot
            dad_reply (bool): if `True`, and message with "I'm {}..." will
                be replied to by the bot.
        """
        self.bot = bot
        self.pog_reply = pog_reply
        self.dad_reply = dad_reply

    async def flip(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with coin flip

        Args:
            ctx (Context): context from command call
        """
        rand = random.randint(1, 2)
        msg = 'heads' if rand == 1 else 'tails'
        await self.bot.message_guild('{}'.format(msg), ctx.channel)

    async def odds(self, ctx: commands.Context, num: int) -> None:
        """Message `ctx.channel` with random int in [1, `num`]

        Args:
            ctx (Context): context from command call
            num (int): maximum range to sample number from
        """
        rand = random.randint(1, num)
        await self.bot.message_guild('{}'.format(rand), ctx.channel)

    async def snowball(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` to tell `ctx.message.author` if they should take the snowball

        Hint: you should always take the snowball

        Args:
            ctx (Context): context from command call
        """
        msg = '{}, you should always take the snowball'.format(
              ctx.message.author.mention)
        await self.bot.message_guild(msg, ctx.channel)

    async def meme_reply(self, message: discord.Message) -> None:
        """Helper method for handling pog and dad joke replies

        Args:
            message (Message): message to parse
        """
        if self.pog_reply:
            text = message.content.lower()
            if re.search(POG_RE, text) or re.search(POG_EMOTE_RE, text):
                await self.bot.message_guild(
                    'poggers', message.channel, POG_EMOTES)

        if self.dad_reply:
            search = re.findall(DAD_RE, text)
            if len(search) > 0:
                search = search[0]
                await self.bot.message_guild(
                    'Hi {}, I\'m {}!'.format(search[4], self.bot.user.mention),
                    message.channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Called when message is created and sent

        Calls `meme_reply()`.
        """
        if not message.author.bot:
            await self.meme_reply(message)

    @commands.command(name='flip', pass_context=True, brief='flip a coin')
    async def _flip(self, ctx: commands.Context) -> None:
        await self.flip(ctx)

    @commands.command(name='odds', pass_context=True, brief='what are the odds? [max_num]')
    async def _odds(self, ctx: commands.Context, num: int) -> None:
        await self.odds(ctx, num)

    @commands.command(name='snowball', pass_context=True, brief='should I snowball?')
    async def _snowball(self, ctx: commands.Context) -> None:
        await self.snowball(ctx)
