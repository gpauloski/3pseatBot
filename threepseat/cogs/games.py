import json
import os
import random

from discord.ext import commands
from typing import Callable, Any

from threepseat.utils import is_admin


class Games(commands.Cog):
    """Extension for picking games to play

    TODO(gpauloski): we should use the guild ID as the key instead of the name
    """
    def __init__(self,
                 bot: commands.Bot,
                 games_file: str) -> None:
        self.bot = bot
        self.games_dict = {}
        self.games_file = games_file

        if os.path.exists(self.games_file):
            with open(self.games_file) as f:
                self.games_dict = json.load(f)       


    @commands.group(pass_context=True, brief='?help games for more info')
    async def games(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.list(ctx)


    @games.command(pass_context=True, brief='list available games')
    async def list(self, ctx: commands.Context) -> None:
        if await self.is_empty(ctx):
            return
        msg = 'games to play:\n```\n'
        games = sorted(self.games_dict[ctx.guild.name])
        for game in games:
            msg += '{}\n'.format(game)
        msg += '```'
        await self.bot.message_guild(msg, ctx.channel)


    @games.command(pass_context=True, brief='pick a random game')
    async def roll(self, ctx: commands.Context) -> None:
        if await self.is_empty(ctx):
            return
        games = self.games_dict[ctx.guild.name]
        await self.bot.message_guild( 
                'you should play {}'.format(random.choice(games)),
                ctx.channel)


    @games.command(pass_context=True, brief='add game')
    async def add(self, ctx: commands.Context, name: str) -> None:
        if is_admin(ctx.message.author):
            if ctx.guild.name not in self.games_dict:
                self.games_dict[ctx.guild.name] = []

            if name not in self.games_dict[ctx.guild.name]:
                self.games_dict[ctx.guild.name].append(name)
                self.save_config()
                await self.bot.message_guild('added {}'.format(name), ctx.channel)
            else:
                await self.bot.message_guild('{} already in list'.format(name), ctx.channel)
        else:
            await self.bot.message_guild(
                    'you do not have permission for this command',
                    ctx.channel)


    @games.command(pass_context=True, brief='remove game')
    async def remove(self, ctx: commands.Context, name: str) -> None:
        if is_admin(ctx.message.author):
            if ctx.guild.name not in self.games_dict:
                self.games_dict[ctx.guild.name] = []

            if name in self.games_dict[ctx.guild.name]:
                self.games_dict[ctx.guild.name].remove(name)
                self.save_config()
                await self.bot.message_guild('removed {}'.format(name), ctx.channel)
            else:
                await self.bot.message_guild('{} not in list'.format(name), ctx.channel)
        else:
            await self.bot.message_guild(
                    'you do not have permission for this command',
                    ctx.channel)

    async def is_empty(self, ctx: commands.Context) -> bool:
        """Check if games list for guild is empty and notify"""
        if ctx.guild.name not in self.games_dict:
            self.games_dict[ctx.guild.name] = []

        if len(self.games_dict[ctx.guild.name]) == 0:
            await self.bot.message_guild( 
                    'There are no games to play. Add more with '
                    '{}games add [title]'.format(self.bot.command_prefix),
                    ctx.channel)
            return True
        return False

    def save_config(self) -> None:
        with open(self.games_file, 'w') as f:
            json.dump(self.games_dict, f, indent=4, sort_keys=True)