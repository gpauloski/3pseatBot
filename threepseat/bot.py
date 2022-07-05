from __future__ import annotations

import logging

import discord
from discord.ext import commands

from threepseat.commands.commands import registered_commands
from threepseat.commands.custom import CustomCommands
from threepseat.config import Config

logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    """3pseatBot."""

    def __init__(self, config: Config) -> None:
        """Init Bot.

        Args:
            config (Config): configuration.
        """
        self.config = config
        self.custom_commands = CustomCommands(
            self,
            db_path=self.config.sqlite_database,
        )

        intents = discord.Intents(
            guilds=True,
            members=True,
            voice_states=True,
            messages=True,
        )

        super().__init__(
            # We are not using command prefixes right now
            command_prefix='???',
            description=None,
            intents=intents,
        )

    async def on_ready(self) -> None:
        """Bot on ready event."""
        await self.wait_until_ready()
        await self.setup()
        logger.info(f'{self.user.name} (Client ID: {self.user.id}) is ready!')

    async def setup(self) -> None:
        """Setup operations to perform once bot is ready."""
        await self.change_presence(
            activity=discord.Game(name=self.config.playing_title),
        )

        self.tree.clear_commands(guild=None)
        for guild in self.guilds:
            self.tree.clear_commands(guild=guild)

        for command in registered_commands():
            self.tree.add_command(command)

        logger.info(f'registered {len(registered_commands())} app commands')

        self.tree.add_command(self.custom_commands)
        await self.custom_commands.register_all()
        logger.info('registered custom commands')

        await self.tree.sync()
        for guild in self.guilds:
            await self.tree.sync(guild=guild)

    async def start(self) -> None:
        """Start the bot."""
        await super().start(self.config.bot_token, reconnect=True)
