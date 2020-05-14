import json
import os
import traceback
import random
import sys
import discord

from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.config_file = 'game_config.json'
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


class Minecraft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {'name': 'none', 'ip': 'none'}
        self.config_file = 'mc_config.json'
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file) as f:
                self.config = json.load(f)

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    async def _is_allowed_in_guild(self, ctx):
        if ctx.message.guild.name not in self.bot.whitelist_guilds:
            await self.bot.send_message(ctx.channel, 
                    'This command is not authorized on this server')
            return False
        return True

    @commands.command(name='mc', pass_context=True,
                      brief='Minecraft Server Login')
    async def _mc(self, ctx):
        if (await self._is_allowed_in_guild(ctx)):
            admin = self.bot.get_user(ctx.guild, self.bot.admins[0])
            msg = ('To login to the {} server:\n'
                   '(1) Join the server using IP: {}\n'
                   '(2) Message {} for whitelist'.format(
                   self.config['name'], self.config['ip'], admin.mention))
            await self.bot.send_message(ctx.channel, msg)

    @commands.command(name='mcname', pass_context=True,
                      brief='Update Minecraft Server name')
    async def _change_name(self, ctx, name):
        if (await self._is_allowed_in_guild(ctx) and 
            self.bot.is_admin(ctx.guild, ctx.message.author)):
            self.config['name'] = name
            self.save_config()
            await self.bot.send_message(ctx.channel,
                    'Updated name to {}.'.format(name))

    @commands.command(name='mcip', pass_context=True,
                      brief='Update Minecraft Server IP')
    async def _change_ip(self, ctx, ip):
        if (await self._is_allowed_in_guild(ctx) and 
            self.bot.is_admin(ctx.guild, ctx.message.author)):
            self.config['ip'] = ip
            self.save_config()
            await self.bot.send_message(ctx.channel,
                    'Updated IP to {}.'.format(ip))


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='3pseat', pass_context=True, 
                      brief='What is 3pseat?')
    async def _threepseat(self, ctx):
        msg = '{}, you must start all messages with {}'.format(
              ctx.message.author.mention, self.bot.message_prefix[0])
        await self.bot.send_message(ctx.channel, msg)

    @commands.command(name='list', pass_context=True, brief='List the strikes')
    async def _list(self, ctx):
        msg = '{}, here are the strikes:```'.format(
              ctx.message.author.mention)
        serverCount = 0
        for user in self.bot.db.get_table(ctx.message.guild.name):
            if user['name'] != 'server':
    	        msg = msg + '\n{}: {}/{}'.format(
                      user['name'], user['count'], self.bot.max_offenses)
            else:
                serverCount = user['count']
        msg = msg + '```\nTotal offenses to date: {}'.format(serverCount)
        await self.bot.send_message(ctx.channel, msg)

    @commands.command(name='source', pass_context=True, 
                      brief='3pseatBot source code')
    async def _3pseat(self, ctx):
        msg = ('3pseatBot\'s source code can be found here: '
               'https://github.com/gpauloski/3pseatBot')
        await self.bot.send_message(ctx.channel, msg)

    @commands.command(name='yeet', pass_context=True, brief='Yeet tha boi')
    async def _yeet(self, ctx, user: discord.Member):
        if not ctx.message.author.guild_permissions.administrator:
            msg = '{}, you do not have yeet (admin) power.'.format(
                  ctx.message.author.mention)
            await self.bot.send_message(ctx.channel, msg)
        elif user.bot:
            msg = '{}, you cannot yeet a bot.'.format(
                  ctx.message.author.mention)
            await self.bot.send_message(ctx.channel, msg)
        else:
            await self.bot.kick_player(ctx.guild, ctx.channel, user)

    @commands.command(name='addstrike', pass_context=True, brief='Add strike')
    async def _add_strike(self, ctx, user: discord.Member):
        if self.bot.is_admin(ctx.guild, ctx.message.author):
            await self.bot.add_strike(ctx.guild, ctx.channel, user)

    @commands.command(name='removestrike', pass_context=True, 
                      brief='Remove strike')
    async def _remove_strike(self, ctx, user: discord.Member):
        if self.bot.is_admin(ctx.guild, ctx.message.author):
            self.bot.remove_strike(ctx.guild, ctx.channel, user)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if (isinstance(error, commands.MissingRequiredArgument) or
            isinstance(error, commands.TooManyArguments)):
            await self.bot.send_message(ctx.channel,
                    "Incorrect number of arguments in command.")
        elif isinstance(error, commands.CommandNotFound):
            await self.bot.handle_mistake(ctx.message)
        elif isinstance(error, commands.BadArgument):
            await self.bot.send_message(ctx.channel,
                    "Invalid argument to command.")
        else:
            traceback.print_exception(type(error), error, error.__traceback__,
                                      file=sys.stderr)

def setup(bot):
    bot.add_cog(General(bot))
    bot.add_cog(Games(bot))
    bot.add_cog(Minecraft(bot))
