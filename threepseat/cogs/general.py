import discord
import traceback
import traceback
import sys

from discord.ext import commands

from threepseat import Bot


class General(commands.Cog):
    """Extension for general features and commands

    Adds the following commands:
      - `?source`: link the 3pseatBot source code
      - `?yeet @Member`: kicks member from guild

    Catches common command errors to provide more helpful feedback
    from the bot when commands fail.
    """
    def __init__(self, bot: Bot) -> None:
        """
        Args:
            bot (Bot): bot that loaded this cog
        """
        self.bot = bot

    async def source(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with link to source code

        Args:
            ctx (Context): context from command call       
        """
        msg = ('3pseatBot\'s source code can be found here: '
               'https://github.com/gpauloski/3pseatBot')
        await self.bot.message_guild(msg, ctx.channel, ignore_prefix=True)

    async def yeet(self, ctx: commands.Context, member: discord.Member) -> None:
        """Kicks `member` from `ctx.guild`

        The caller of the command (i.e. `ctx.message.author`) must have
        kick permission in the guild.

        Args:
            ctx (Context): context from command call       
        """
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
        """Handle common command errors

        Catches `MissingRequiredArgument`, `TooManyArguments`, and
        `BadArgument` errors.

        Args:
            ctx (Context): context from command call 
            error (CommandError): error raised by the API
        """
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

    @commands.command(name='source', pass_context=True, brief='3pseatBot source code')
    async def _source(self, ctx: commands.Context) -> None:
        await self.source(ctx)

    @commands.command(name='yeet', pass_context=True, brief='yeet tha boi')
    async def _yeet(self, ctx: commands.Context, member: discord.Member) -> None:
        await self.yeet(ctx, member)