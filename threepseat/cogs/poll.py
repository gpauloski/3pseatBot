import discord
import emoji
import traceback

from discord.ext import commands

from threepseat.bot import Bot
from threepseat.utils import is_admin


NUMBERS = {
    1: emoji.emojize(':one:', use_aliases=True),
    2: emoji.emojize(':two:', use_aliases=True),
    3: emoji.emojize(':three:', use_aliases=True),
    4: emoji.emojize(':four:', use_aliases=True),
    5: emoji.emojize(':five:', use_aliases=True),
    6: emoji.emojize(':six:', use_aliases=True),
    7: emoji.emojize(':seven:', use_aliases=True),
    8: emoji.emojize(':eight:', use_aliases=True),
    9: emoji.emojize(':nine:', use_aliases=True)
}


class Poll(commands.Cog):
    """Extension for starting polls.

    Adds the following commands:
      - `?poll "[question]" "[option 1]" "[option 2]" ... "[option 9]"`
    """
    def __init__(self,
                 bot: Bot,
                 guild_admin_permission: bool = True,
                 bot_admin_permission: bool = True,
                 everyone_permission: bool = False
    ) -> None:
        """
        Args:
            bot (Bot): bot that loaded this cog
            guild_admin_permission (bool): can guild admins start polls
            bot_admin_permission (bool): can bot admin start polls
            everyone_permission (bool): allow everyone to start polls
        """
        self.bot = bot
        self.guild_admin_permission = guild_admin_permission
        self.bot_admin_permission = bot_admin_permission
        self.everyone_permission = everyone_permission

    async def create_poll(self,
                          ctx: commands.Context,
                          question: str,
                          *options: str
    ) -> None:
        """Message `ctx.channel` with the formatted poll

        Args:
            ctx (Context): context from command call
            question (str): question
            options (list[str]): up to 9 response options
        """
        if not self.has_permission(ctx.message.author):
            await self.bot.message_guild(
                '{}, you do not have permission to start a poll'.format(
                    ctx.message.author.mention),
                ctx.channel)
            return
        if len(options) == 0:
            await self.bot.message_guild(
                '{}, no voting options were provided'.format(
                    ctx.message.author.mention),
                ctx.channel)
            return
        if len(options) > 9:
            await self.bot.message_guild(
                '{}, a maximum of 9 options can be provided'.format(
                    ctx.message.author.mention),
                ctx.channel)
            return
        msg = 'vote by reacting:\n\n**{}**\n'.format(question)
        numbers = []
        for i, option in enumerate(options, 1):
            num_emoji = NUMBERS[i]
            msg += '{} {}\n'.format(num_emoji, option)
            numbers.append(num_emoji)
        await self.bot.message_guild(msg, ctx.channel, react=numbers)

    def has_permission(self, member: discord.Member) -> bool:
        """Does a member have permission to use the poll command"""
        if self.everyone_permission:
            return True
        if is_admin(member) or self.bot.is_bot_admin(member):
            return True
        return False

    @commands.Cog.listener()
    async def on_command_error(self,
                                ctx: commands.Context,
                                error: commands.CommandError
        ) -> None:
        """Catch unknown errors to see if they are actually a user command

        Args:
            ctx (Context): context from command call
            error (CommandError): error raised by the API
        """
        if isinstance(error, commands.CommandNotFound):
            # Ignore commands that have their own error handlers
            print(ctx.__dict__)
        else:
            raise error

    @commands.command(name='poll',
                      pass_context=True,
                      brief='Start poll: "question" "option 1" "option 2" ...'
    )
    async def _poll(self,
                    ctx: commands.Context,
                    question: str,
                    *options: str
    ) -> None:
        await self.create_poll(ctx, question, *options)

    @_poll.error
    async def _poll_error(self,
                          ctx: commands.Context,
                          error: commands.CommandError
    ) -> None:
        """Handle invalid usage of poll command
        Args:
            ctx (Context): context from command call
            error (CommandError): error raised by the API
        """
        if isinstance(error, commands.MissingRequiredArgument):
            await self.bot.message_guild(
                    'the format for the poll command is:\n'
                    '> {}poll "question" "option 1" "option 2" ... "option 9"'
                    '\nQuotation marks can be ignored for single '
                    'word options.'.format(self.bot.command_prefix),
                    ctx.channel)
        else:
            raise error