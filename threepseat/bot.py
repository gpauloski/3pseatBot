from __future__ import annotations

import logging

import discord
from discord.ext import commands

from threepseat.commands.commands import registered_app_commands
from threepseat.ext.extension import CommandGroupExtension
from threepseat.listeners.listeners import registered_listeners


logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    """3pseatBot."""

    def __init__(
        self,
        *,
        playing_title: str | None = None,
        extensions: list[CommandGroupExtension] | None = None,
    ) -> None:
        """Init Bot.

        Args:
            playing_title (str, optional): set bot as playing this title
                (default: None).
            extensions (list[CommandGroupExtension], optional): list of
                extensions to register with the bot.
        """
        self.playing_title = playing_title
        self._cmd_group_exts = extensions

        intents = discord.Intents(
            guilds=True,
            members=True,
            voice_states=True,
            messages=True,
            message_content=True,
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
        # Should not be none as we have waited for the login to succeed
        assert self.user is not None
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

        commands = registered_app_commands()
        for command in commands:
            self.tree.add_command(command)
        logger.info(f'registered {len(commands)} app commands')

        listeners = registered_listeners()
        for listener in listeners:
            self.add_listener(listener.func, listener.event)
        logger.info(f'registered {len(listeners)} listeners')

        if self._cmd_group_exts is not None:
            for ext in self._cmd_group_exts:
                self.tree.add_command(ext)
                await ext.post_init(self)
                logger.info(f'registered {ext.name} command group')

        await self.tree.sync()
        for guild in self.guilds:
            await self.tree.sync(guild=guild)
