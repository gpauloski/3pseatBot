"""Cog with general utility functions"""
import random

from discord.ext import commands

from threepseat.bot import Bot


class General(commands.Cog):
    """Extension for general features and commands

    Adds the following commands:
      - `?source`: link the 3pseatBot source code
      - `?flip`: flips a coin
      - `?odds [num]`: give random integer in [1, number]

    Catches common command errors to provide more helpful feedback
    from the bot when commands fail.
    """

    def __init__(self, bot: Bot) -> None:
        """Init General

        Args:
            bot (Bot): bot that loaded this cog
        """
        self.bot = bot

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

    async def source(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with link to source code

        Args:
            ctx (Context): context from command call
        """
        msg = (
            '3pseatBot\'s source code can be found here: '
            'https://github.com/gpauloski/3pseatBot'
        )
        await self.bot.message_guild(msg, ctx.channel, ignore_prefix=True)

    @commands.command(
        name='flip', pass_context=True, brief='flip a coin', ignore_extra=False
    )
    async def _flip(self, ctx: commands.Context) -> None:
        await self.flip(ctx)

    @commands.command(
        name='odds',
        pass_context=True,
        brief='get a random number in a range',
        ignore_extra=False,
        description='Print a random integer between 1 and <int>',
    )
    async def _odds(self, ctx: commands.Context, num: int) -> None:
        await self.odds(ctx, num)

    @commands.command(
        name='source',
        pass_context=True,
        brief='3pseatBot source code',
        ignore_extra=False,
    )
    async def _source(self, ctx: commands.Context) -> None:
        await self.source(ctx)
