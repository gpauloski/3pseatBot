from __future__ import annotations

import logging

import discord
from discord.ext import commands

from threepseat.commands.commands import registered_app_commands
from threepseat.ext.extension import CommandGroupExtension
from threepseat.listeners.listeners import registered_listeners
from threepseat.logging import log_timing

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
        # on_ready fires on every (re)connect, so setup() above re-runs and
        # re-syncs the tree each time; the guild count makes repeats legible.
        logger.info(
            '%s (Client ID: %s) is ready! (%s guild(s))',
            self.user.name,
            self.user.id,
            len(self.guilds),
        )

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
        logger.info('registered %s app commands', len(commands))

        listeners = registered_listeners()
        for listener in listeners:
            self.add_listener(listener.func, listener.event)
        logger.info('registered %s listeners', len(listeners))

        if self._cmd_group_exts is not None:
            for ext in self._cmd_group_exts:
                self.tree.add_command(ext)
                try:
                    await ext.post_init(self)
                except Exception:
                    # Isolate a failing extension so one bad post_init (e.g.
                    # restoring persisted state) does not abort startup for the
                    # rest, and name it so the failure is diagnosable.
                    logger.exception(
                        'post_init failed for %s command group',
                        ext.name,
                    )
                else:
                    logger.info('registered %s command group', ext.name)

        # Syncing is a batch of Discord API round-trips (global + one per
        # guild) and is the slowest part of startup, so time it.
        with log_timing(
            logger,
            'synced command tree across %s guild(s)',
            len(self.guilds),
        ):
            await self.tree.sync()
            for guild in self.guilds:
                await self.tree.sync(guild=guild)
