import discord
import logging
import threepseat

from discord.ext import commands
from typing import Union, Optional, List, Dict


logger = logging.getLogger()


class Bot(commands.Bot):
    """

    """
    def __init__(self,
                 token: str,
                 *,
                 command_prefix: str = '!',
                 ignore_prefix: List[str] = [],
                 bot_admins: List[str] = [],
                 playing_title: Optional[str] = None,
                 use_extensions: List[str] = [],
                 extension_configs: Dict[str, dict],
        ) -> None:
        """
        """
        self.token = token
        self.command_prefix = command_prefix
        self.ignore_prefix = ignore_prefix
        self.bot_admins = bot_admins
        self.playing_title = playing_title
        self.use_extensions = use_extensions
        self.extension_configs = extension_configs 
        self.guild_message_prefix = ''

        super().__init__(command_prefix=self.command_prefix)


    def is_bot_admin(self, user: Union[discord.User, discord.Member]) -> bool:
        return str(user) in self.bot_admins


    async def message_user(self, 
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


    async def message_guild(self, 
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


    async def _message(self, 
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
    

    def run(self):
        super().run(self.token, reconnect=True)