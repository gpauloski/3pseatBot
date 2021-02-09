import json
import os
import random

from discord.ext import commands
from typing import Callable, Any

from threepseat import Bot
from threepseat.utils import is_admin


class Games(commands.Cog):
    """Extension for picking games to play.

    Adds the following commands:
      - `?games`: aliases `list`
      - `?games list`: list games for the guild
      - `?games roll`: pick a random game to play
      - `?games add [title]`: add a game to list for this guild
      - `?games remove [title]`: remove a game from this guild
    """
    def __init__(self, bot: Bot, games_file: str) -> None:
        """
        Args:
            bot (Bot): bot that loaded this cog
            games_file (str): path to store json data
        """
        self.bot = bot
        self.games_dict = {}
        self.games_file = games_file

        if os.path.exists(self.games_file):
            with open(self.games_file) as f:
                self.games_dict = json.load(f)       

    async def list(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with list of games for guild

        Args:
            ctx (Context): context from command call
        """
        if await self.is_empty(ctx):
            return
        msg = 'games to play:\n```\n'
        games = sorted(self.games_dict[ctx.guild.name])
        for game in games:
            msg += '{}\n'.format(game)
        msg += '```'
        await self.bot.message_guild(msg, ctx.channel)

    async def roll(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with random game to play

        Args:
            ctx (Context): context from command call
        """
        if await self.is_empty(ctx):
            return
        games = self.games_dict[ctx.guild.name]
        await self.bot.message_guild( 
                'you should play {}'.format(random.choice(games)),
                ctx.channel)

    async def add(self, ctx: commands.Context, name: str) -> None:
        """Add a new game to the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): title of game to add
        """
        if is_admin(ctx.message.author):
            if ctx.guild.name not in self.games_dict:
                self.games_dict[ctx.guild.name] = []

            if name not in self.games_dict[ctx.guild.name]:
                self.games_dict[ctx.guild.name].append(name)
                self._save_games()
                await self.bot.message_guild('added {}'.format(name), ctx.channel)
            else:
                await self.bot.message_guild('{} already in list'.format(name), ctx.channel)
        else:
            await self.bot.message_guild(
                    'you do not have permission for this command',
                    ctx.channel)

    async def remove(self, ctx: commands.Context, name: str) -> None:
        """Remove a game from the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): title of game to remove
        """
        if is_admin(ctx.message.author):
            if ctx.guild.name not in self.games_dict:
                self.games_dict[ctx.guild.name] = []

            if name in self.games_dict[ctx.guild.name]:
                self.games_dict[ctx.guild.name].remove(name)
                self._save_games()
                await self.bot.message_guild('removed {}'.format(name), ctx.channel)
            else:
                await self.bot.message_guild('{} not in list'.format(name), ctx.channel)
        else:
            await self.bot.message_guild(
                    'you do not have permission for this command',
                    ctx.channel)

    async def is_empty(self, ctx: commands.Context) -> bool:
        """Check if games list

        Sends message to the channel if the guild has no games added.
        This function acts as a helper for the commands added by this cog.

        Args:
            ctx (Context): context from command call

        Returns:
            `True` if the guild has no games else `False`
        """
        if ctx.guild.name not in self.games_dict:
            self.games_dict[ctx.guild.name] = []

        if len(self.games_dict[ctx.guild.name]) == 0:
            await self.bot.message_guild( 
                    'There are no games to play. Add more with '
                    '{}games add [title]'.format(self.bot.command_prefix),
                    ctx.channel)
            return True
        return False

    def _save_games(self) -> None:
        """Write games data to file"""
        with open(self.games_file, 'w') as f:
            json.dump(self.games_dict, f, indent=4, sort_keys=True)

    @commands.group(name='games', pass_context=True, brief='?help games for more info')
    async def _games(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.list(ctx)

    @_games.command(name='list', pass_context=True, brief='list available games')
    async def _list(self, ctx: commands.Context) -> None:
        await self.list(ctx)

    @_games.command(name='roll', pass_context=True, brief='pick a random game')
    async def _roll(self, ctx: commands.Context) -> None:
        await self.roll(ctx)

    @_games.command(name='add', pass_context=True, brief='add game')
    async def _add(self, ctx: commands.Context, name: str) -> None:
        await self.add(ctx, name)

    @_games.command(name='remove', pass_context=True, brief='remove game')
    async def _remove(self, ctx: commands.Context, name: str) -> None:
        await self.remove(ctx, name)