"""Cog for randomly getting a game to play"""
import discord
import random

from discord.ext import commands
from typing import List, Optional

from threepseat.bot import Bot
from threepseat.utils import is_admin, GuildDatabase


class Games(commands.Cog):
    """Extension for picking games to play.

    Adds the following commands:
      - `?games`: get options for managing games
      - `?games list`: list games for the guild
      - `?games roll`: pick a random game to play
      - `?games add [title]`: add a game to list for this guild
      - `?games remove [title]`: remove a game from this guild
    """
    def __init__(self, bot: Bot, games_file: str) -> None:
        """Init Games

        Args:
            bot (Bot): bot that loaded this cog
            games_file (str): path to store database
        """
        self.bot = bot
        self.db = GuildDatabase(games_file)

    async def is_empty(self, ctx: commands.Context) -> bool:
        """Check if games list

        Sends message to the channel if the guild has no games added.
        This function acts as a helper for the commands added by this cog.

        Args:
            ctx (Context): context from command call

        Returns:
            `True` if the guild has no games else `False`
        """
        if len(self._get_games(ctx.guild)) == 0:
            await self.bot.message_guild(
                'There are no games to play. Add more with '
                '{}games add [title]'.format(self.bot.command_prefix),
                ctx.channel)
            return True
        return False

    async def list(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with list of games for guild

        Args:
            ctx (Context): context from command call
        """
        if await self.is_empty(ctx):
            return
        msg = 'games to play:\n```\n'
        games = sorted(self._get_games(ctx.guild))
        for game in games:
            msg += '{}\n'.format(game)
        msg += '```'
        await self.bot.message_guild(msg, ctx.channel)

    async def add(self, ctx: commands.Context, name: str) -> None:
        """Add a new game to the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): title of game to add
        """
        if not (is_admin(ctx.message.author) or self.bot.is_bot_admin(ctx.message.author)):
            raise commands.MissingPermissions

        games = self._get_games(ctx.guild)
        if name not in games:
            games.append(name)
            self._set_games(ctx.guild, games)
            await self.bot.message_guild(
                'added {}'.format(name), ctx.channel)
        else:
            await self.bot.message_guild(
                '{} already in list'.format(name), ctx.channel)

    async def remove(self, ctx: commands.Context, name: str) -> None:
        """Remove a game from the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): title of game to remove
        """
        if not (is_admin(ctx.message.author) or self.bot.is_bot_admin(ctx.message.author)):
            raise commands.MissingPermissions

        games = self._get_games(ctx.guild)
        if name in games:
            games.remove(name)
            self._set_games(ctx.guild, games)
            await self.bot.message_guild(
                'removed {}'.format(name), ctx.channel)
        else:
            await self.bot.message_guild(
                '{} not in list'.format(name), ctx.channel)

    async def roll(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with random game to play

        Args:
            ctx (Context): context from command call
        """
        if await self.is_empty(ctx):
            return
        games = self._get_games(ctx.guild)
        await self.bot.message_guild(
            'you should play {}'.format(random.choice(games)), ctx.channel)

    def _get_games(self, guild: discord.Guild) -> Optional[list]:
        """Get list of games for guild from database"""
        games = self.db.value(guild, 'games')
        if games is None:
            return []
        return games

    def _set_games(self, guild: discord.Guild, games: List[str]) -> None:
        """Set list of games for guild in database"""
        self.db.set(guild, 'games', games)

    @commands.group(
        name='games',
        pass_context=True,
        brief='manage list of games for the guild')
    async def _games(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.bot.message_guild(
                'use the `add/list/remove/roll` subcommands. '
                'See `{}help {}` for more info'.format(
                    self.bot.command_prefix, ctx.invoked_with),
                ctx.channel)

    @_games.command(
        name='list',
        pass_context=True,
        brief='list available games',
        ignore_extra=False,
        description='List games added to the guild'
    )
    async def _list(self, ctx: commands.Context) -> None:
        await self.list(ctx)

    @_games.command(
        name='add',
        pass_context=True,
        brief='add game',
        description='Add a new game to the guild\'s list'
    )
    async def _add(self, ctx: commands.Context, *, name: str) -> None:
        await self.add(ctx, name)

    @_games.command(
        name='remove',
        pass_context=True,
        brief='remove game',
        description='Remove a game for the guild\'s list'
    )
    async def _remove(self, ctx: commands.Context, *, name: str) -> None:
        await self.remove(ctx, name)

    @_games.command(
        name='roll',
        pass_context=True,
        brief='pick a random game',
        ignore_extra=False,
        description='Get a random game to play from the guild\'s list'
    )
    async def _roll(self, ctx: commands.Context) -> None:
        await self.roll(ctx)
