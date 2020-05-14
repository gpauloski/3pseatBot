import json
import os
import random

from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.config_file = 'data/game_config.json'
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file) as f:
                self.config = json.load(f)

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    def _handle_missing_key(self, guild):
        if guild not in self.config:
            self.config[guild] = []

    def _add(self, guild, name):
        self._handle_missing_key(guild)
        if name not in self.config[guild]:
            self.config[guild].append(name)
        self.save_config()

    def _remove(self, guild, index):
        self._handle_missing_key(guild)
        if index >= len(self.config[guild]):
            return None
        removed = self.config[guild].pop(index)
        self.save_config()
        return removed

    async def _warn_if_no_games(self, ctx):
        if len(self.config[ctx.guild.name]) == 0:
            await self.bot.send_message(ctx.channel, 
                    'There are no games to play. Add more with '
                    '{}add.'.format(self.bot.command_prefix))
            return True
        return False

    @commands.command(name='games', pass_context=True,
                      brief='List games to play')
    async def _games(self, ctx):
        self._handle_missing_key(ctx.guild.name)
        if await self._warn_if_no_games(ctx):
            return
        msg = 'Games to play:\n```'
        for i, game in enumerate(self.config[ctx.guild.name]):
            msg += '({}) {}\n'.format(i, game)
        msg += '```'
        await self.bot.send_message(ctx.channel, msg)

    @commands.command(name='roll', pass_context=True,
                      brief='Pick a random game')
    async def _roll(self, ctx):
        self._handle_missing_key(ctx.guild.name)
        if await self._warn_if_no_games(ctx):
            return
        games = self.config[ctx.guild.name]
        await self.bot.send_message(ctx.channel, 
                'You should play {}'.format(random.choice(games)))

    @commands.command(name='add', pass_context=True,
                      brief='Add game to list')
    async def _add_game(self, ctx, name):
        if self.bot.is_admin(ctx.guild, ctx.message.author):
            self._add(ctx.guild.name, name)
            await self.bot.send_message(ctx.channel,
                    'added {}'.format(name))

    @commands.command(name='remove', pass_context=True,
                      brief='Remove game by index')
    async def _remove_game(self, ctx, index):
        if self.bot.is_admin(ctx.guild, ctx.message.author):
            removed_game = self._remove(ctx.guild.name, int(index))
            if removed_game is None:
                await self.bot.send_message(ctx.channel, 'Index out of range')
            else:
                await self.bot.send_message(ctx.channel,
                        'removed {}'.format(removed_game))

def setup(bot):
    bot.add_cog(Games(bot))
