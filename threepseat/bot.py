"""3pseatBot base class"""
import discord
import logging
import threepseat

from discord.ext import commands
from typing import Union, Optional, List, Dict


logger = logging.getLogger()


class Bot(commands.Bot):
    """3pseatBot

    This class manages cogs/extensions and implements some minimal
    functionality needed by the cogs.
    """
    def __init__(
        self,
        token: str,
        *,
        command_prefix: str = '!',
        bot_admins: List[int] = [],
        playing_title: Optional[str] = None,
        use_extensions: List[str] = [],
        extension_configs: Dict[str, Dict],
    ) -> None:
        """Init Bot

        Args:
            token (int): Discord bot token needed for authentication
            command_prefix (str): prefix for all bot commands (including
                extensions).
            bot_admins (list[int]): list of Discord user IDs for admins of
                this bot. Note that bot admins are different from Discord
                admins.
            playing_title (str): if not None, the game displayed as what the
                bot is playing.
            use_extensions (list[str]): list of extension names to load
            extension_configs (dict[str, dict]): dict containing arguments
                to cogs where the keys to the dict are cog names. For example,
                if the cog 'games' is loaded, then `**extension_configs[games]`
                will be passed to the `Games` constructor. Note that a config
                does not have to be provided (i.e. default values will be used
                if a config is not present for a loaded cog).
        """
        self.token = token
        self.command_prefix = command_prefix
        self.bot_admins = bot_admins
        self.playing_title = playing_title
        self.use_extensions = use_extensions
        self.extension_configs = extension_configs
        self.guild_message_prefix = ''

        intents = discord.Intents.default()
        intents.members = True

        super().__init__(command_prefix=self.command_prefix, intents=intents)

    def is_bot_admin(self, user: Union[discord.User, discord.Member]) -> bool:
        """Is user an admin of this bot"""
        return user.id in self.bot_admins

    async def message_user(
        self,
        message: str,
        user: Union[discord.User, discord.Member],
        react: Optional[Union[str, List[str]]] = None
    ) -> discord.Message:
        """Message user

        Args:
            message (str)
            user (`User` or `Member`)
            react (str, list[str], optional): reactions to add to message
                (default: None)

        Returns:
            `Message`
        """
        logger.info('Direct message {}: {}'.format(user, message))
        channel = await user.create_dm()
        return await self._message(message, channel, react)

    async def message_guild(
        self,
        message: str,
        channel: discord.TextChannel,
        react: Optional[Union[str, List[str]]] = None,
        ignore_prefix: bool = False
    ) -> discord.Message:
        """Message Guild Channel

        Args:
            message (str)
            channel (`Channel`)
            react (str, list[str], optional): reactions to add to message
                (default: None)

        Returns:
            `Message`
        """
        if not ignore_prefix:
            message = self.guild_message_prefix + ' ' + message
        logger.info('Message guild={}, channel={}: {}'.format(
            channel.guild, channel, message))
        return await self._message(message, channel, react)

    async def _message(
        self,
        message: str,
        channel: discord.abc.Messageable,
        react: Optional[Union[str, List[str]]] = None
    ) -> discord.Message:
        """Send message in channel

        Args:
            message (str)
            channel (`Messageable`)
            react (str, list[str], optional): reactions to add to message
                (default: None)

        Returns:
            `Message`
        """
        msg = await channel.send(message)
        if react is not None:
            if isinstance(react, str):
                await msg.add_reaction(react)
            elif isinstance(react, list):
                for r in react:
                    await msg.add_reaction(r)
        return msg

    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        if self.playing_title is not None:
            await self.change_presence(
                activity=discord.Game(name=self.playing_title))

        logger.info('Logged in as {} (ID={})'.format(
            self.user.name, self.user.id))

        # Load extensions/cogs
        for ext in self.use_extensions:
            if ext in threepseat.cogs.EXTENSIONS:
                # Load a cog we know
                _class = threepseat.cogs.EXTENSIONS[ext]

                if ext in self.extension_configs:
                    config = self.extension_configs[ext]
                else:
                    config = {}

                self.add_cog(_class(self, **config))
            else:
                # Try and load custom cog with setup()
                try:
                    self.load_extension(ext)
                except Exception as e:
                    logger.warning('Failed to load extension {}. '
                                   'Does this file exist in the '
                                   'cogs/ directory?'.format(ext))
                    raise e

            logger.info('Loaded extension: {}'.format(ext))
        await self.wait_until_ready()
        logger.info('Bot is ready!')

    async def on_command_error(
        self,
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
        cmd = ctx.invoked_with
        if ctx.invoked_subcommand is not None:
            cmd = ctx.invoked_subcommand.full_parent_name + ' ' + ctx.invoked_with
        if isinstance(error, commands.MissingRequiredArgument):
            msg = ('missing required options for command. '
                   'Try `?help {}` for more info'.format(cmd))
        elif isinstance(error, commands.TooManyArguments):
            msg = ('too many options for command. '
                   'Try `?help {}` for more info'.format(cmd))
        elif isinstance(error, commands.BadArgument):
            msg = ('invalid option for command. '
                   'Try `?help {}` for more info'.format(cmd))
        elif isinstance(error, commands.ExpectedClosingQuoteError):
            msg = 'missing closing quotation mark in command'
        elif isinstance(error, commands.CommandNotFound):
            msg = 'I do not know that command. Try `?help` for a list of commands'
        elif isinstance(error, commands.BadBoolArgument):
            msg = 'unable to convert the option to true or false'
        elif isinstance(error, commands.MissingPermissions):
            msg = ('{}, you do not have permission to use that '
                   'command'.format(ctx.message.author.mention))
        elif isinstance(error, commands.BotMissingPermissions):
            msg = 'I do not have permission to run this command on this guild'
        else:
            msg = 'oops command failed. See the logs for more info'
            logger.error('{}: {}\n{}'.format(
                type(error), error, error.__traceback__))
        await self.message_guild(msg, ctx.channel)

    def run(self):
        """Start the bot"""
        super().run(self.token, reconnect=True)
