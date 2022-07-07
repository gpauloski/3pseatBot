from __future__ import annotations

import logging

import discord
from discord.ext import commands

from threepseat.commands.commands import registered_commands
from threepseat.commands.custom import CustomCommands
from threepseat.sounds.commands import SoundCommands
from threepseat.utils import leave_on_empty


logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    """3pseatBot."""

    def __init__(
        self,
        *,
        playing_title: str | None = None,
        custom_commands: CustomCommands | None = None,
        sound_commands: SoundCommands | None = None,
    ) -> None:
        """Init Bot.

        Args:
            playing_title (str, optional): set bot as playing this title
                (default: None).
            custom_commands (CustomCommands, optional): custom commands
                object to register with bot (default: None).
            sound_commands (SoundCommands, optional): sound commands
                object to register with bot (default: None).
        """
        self.playing_title = playing_title
        self.custom_commands = custom_commands
        self.sound_commands = sound_commands

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
        await self.setup()
        await self.wait_until_ready()
        logger.info(f'{self.user.name} (Client ID: {self.user.id}) is ready!')

    async def setup(self) -> None:
        """Setup operations to perform once bot is ready."""
        if self.playing_title is not None:
            await self.change_presence(
                activity=discord.Game(name=self.playing_title),
            )

        self.tree.clear_commands(guild=None)
        for guild in self.guilds:
            self.tree.clear_commands(guild=guild)

        for command in registered_commands():
            self.tree.add_command(command)

        logger.info(f'registered {len(registered_commands())} app commands')

        if self.custom_commands is not None:
            self.tree.add_command(self.custom_commands)
            await self.custom_commands.register_all(self)
            logger.info('registered custom commands')

        if self.sound_commands is not None:
            self.tree.add_command(self.sound_commands)
            logger.info('registered sound commands')
            self.voice_channel_checker = leave_on_empty(self, 30)
            self.voice_channel_checker.start()

        await self.tree.sync()
        for guild in self.guilds:
            await self.tree.sync(guild=guild)
