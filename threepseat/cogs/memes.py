"""Cog for random memes and commands"""
import discord
import re

from discord.ext import commands

from threepseat.bot import Bot
from threepseat.utils import is_admin


POG_EMOTES = ['\U0001F1F5', '\U0001F1F4', '\U0001F1EC']
POG_RE = r'(p+\s*)+(o+\s*)+(g+\s*)+'
POG_EMOTE_RE = r'<:.*pog.*:\d*>'
DAD_RE = r'(^| |\n)((i\'?m)|(i am)) (\w+)'


class Memes(commands.Cog):
    """Extension for Memes

    Adds the following commands:
      - `?snowball`: should you take the snowball?
      - `?yeet @Member`: kicks member from guild
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

    async def snowball(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` to tell `ctx.message.author` if they should take the snowball

        Hint: you should always take the snowball

        Args:
            ctx (Context): context from command call
        """
        msg = '{}, you should always take the snowball'.format(
              ctx.message.author.mention)
        await self.bot.message_guild(msg, ctx.channel)

    async def yeet(self, ctx: commands.Context, member: discord.Member) -> None:
        """Kicks `member` from `ctx.guild`

        The caller of the command (i.e. `ctx.message.author`) must have
        kick permission in the guild.

        Args:
            ctx (Context): context from command call
            member (Member): member to yeet
        """
        if not ctx.message.author.guild_permissions.administrator:
            raise commands.MissingPermissions
        elif member.bot:
            msg = '{}, you cannot yeet a bot.'.format(
                  ctx.message.author.mention)
            await self.bot.message_guild(msg, ctx.channel)
        else:
            if is_admin(member):
                msg = ('Failed to kick {}. Your cognizance is highly '
                       'acknowledged.'.format(member.mention))
                await self.bot.message_guild(msg, ctx.channel)
            else:
                await ctx.guild.kick(member)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Called when message is created and sent

        Calls `meme_reply()`.
        """
        if not message.author.bot:
            await self.meme_reply(message)

    @commands.command(
        name='snowball',
        pass_context=True,
        brief='should I snowball?',
        ignore_extra=False
    )
    async def _snowball(self, ctx: commands.Context) -> None:
        await self.snowball(ctx)

    @commands.command(
        name='yeet',
        pass_context=True,
        brief='yeet tha boi',
        ignore_extra=False,
        description='Kick a member from the guild. Note <member> should '
                    'be a mention.'
    )
    async def _yeet(self, ctx: commands.Context, member: discord.Member) -> None:
        await self.yeet(ctx, member)
