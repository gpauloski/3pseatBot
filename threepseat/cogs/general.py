import discord
import traceback

import traceback
import sys

from discord.ext import commands


class General(commands.Cog):
    """Extension for general features and commands"""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


    @commands.command(name='source', pass_context=True,
                      brief='3pseatBot source code')
    async def source(self, ctx: commands.Context) -> None:
        """Command to link to the bots source code"""
        msg = ('3pseatBot\'s source code can be found here: '
               'https://github.com/gpauloski/3pseatBot')
        await self.bot.message_guild(msg, ctx.channel, ignore_prefix=True)


    @commands.command(name='yeet', pass_context=True, brief='yeet tha boi')
    async def yeet(self, 
                   ctx: commands.Context,
                   member: discord.Member
        ) -> None:
        """Command to kick a member"""
        if not ctx.message.author.guild_permissions.administrator:
            msg = '{}, you do not have yeet (admin) power.'.format(
                  ctx.message.author.mention)
            await self.bot.message_guild(msg, ctx.channel)
        elif user.bot:
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
    async def on_command_error(self, 
                               ctx: commands.Context,
                               error: commands.CommandError
        ) -> None:
        """Handle command errors"""
        if (isinstance(error, commands.MissingRequiredArgument) or
            isinstance(error, commands.TooManyArguments)):
            await self.bot.message_guild(
                    "Incorrect number of arguments in command.",
                    ctx.channel)
        elif isinstance(error, commands.BadArgument):
            await self.bot.message_guild("Invalid argument to command.",
                    ctx.channel)
        else:
            traceback.print_exception(type(error), error, error.__traceback__,
                                      file=sys.stderr)