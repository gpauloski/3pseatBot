import json
import os
import traceback
import sys
import discord

from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='3pseat', pass_context=True,
                      brief='What is 3pseat?')
    async def _threepseat(self, ctx):
        msg = '{}, you must start all messages with {}'.format(
              ctx.message.author.mention, self.bot.message_prefix[0])
        await self.bot.send_server_message(ctx.channel, msg)

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
        await self.bot.send_server_message(ctx.channel, msg)

    @commands.command(name='source', pass_context=True,
                      brief='3pseatBot source code')
    async def _3pseat(self, ctx):
        msg = ('3pseatBot\'s source code can be found here: '
               'https://github.com/gpauloski/3pseatBot')
        await self.bot.send_server_message(ctx.channel, msg)

    @commands.command(name='yeet', pass_context=True, brief='Yeet tha boi')
    async def _yeet(self, ctx, user: discord.Member):
        if not ctx.message.author.guild_permissions.administrator:
            msg = '{}, you do not have yeet (admin) power.'.format(
                  ctx.message.author.mention)
            await self.bot.send_server_message(ctx.channel, msg)
        elif user.bot:
            msg = '{}, you cannot yeet a bot.'.format(
                  ctx.message.author.mention)
            await self.bot.send_server_message(ctx.channel, msg)
        else:
            await self.bot.kick_player(ctx.guild, ctx.channel, user)

    @commands.command(name='addstrike', pass_context=True, brief='Add strike')
    async def _add_strike(self, ctx, user: discord.Member):
        if self.bot.is_admin(ctx.guild, ctx.message.author):
            count = self.bot.add_strike(ctx.guild, user)
            await self.bot.send_server_message(ctx.channel, 
                    'added strike to {}. New strike count is {}.'.format(
                    user.mention, count))
            await self.bot.handle_mistake(ctx.message, count)
        else:
            await self.bot.send_server_message(ctx.channel,
                    'you lack permission')

    @commands.command(name='removestrike', pass_context=True,
                      brief='Remove strike')
    async def _remove_strike(self, ctx, user: discord.Member):
        if self.bot.is_admin(ctx.guild, ctx.message.author):
            count = self.bot.remove_strike(ctx.guild, user)
            await self.bot.send_server_message(ctx.channel, 
                    'removed strike from {}. New strike count is {}.'.format(
                    user.mention, count))
            await self.bot.handle_mistake(ctx.message, count)
        else:
            await self.bot.send_server_message(ctx.channel,
                    'you lack permission')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if (isinstance(error, commands.MissingRequiredArgument) or
            isinstance(error, commands.TooManyArguments)):
            await self.bot.send_server_message(ctx.channel,
                    "Incorrect number of arguments in command.")
        elif isinstance(error, commands.CommandNotFound):
            await self.bot.handle_mistake(ctx.message)
        elif isinstance(error, commands.BadArgument):
            await self.bot.send_server_message(ctx.channel,
                    "Invalid argument to command.")
        else:
            traceback.print_exception(type(error), error, error.__traceback__,
                                      file=sys.stderr)

def setup(bot):
    bot.add_cog(General(bot))
