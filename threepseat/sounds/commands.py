from __future__ import annotations

import discord
from discord import app_commands

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.sounds.data import Sounds


class SoundCommands(app_commands.Group):
    """App commands for sound board."""

    def __init__(self, sounds: Sounds) -> None:
        """Init SoundCommands.

        Args:
            sounds (Sounds): sounds database object.
        """
        self.sounds = sounds

    @app_commands.command(name='add', description='Add a sound')
    @app_commands.describe(name='Name of sound (max 12 characters)')
    @app_commands.describe(link='Link to YouTube clip (max 30 seconds)')
    @app_commands.describe(
        description='Sound description (max 100 characters)',
    )
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        link: str,
        description: str,
    ) -> None:
        """Add a new sound."""
        log_interaction(interaction)

    @app_commands.command(
        name='leave',
        description='Remove the bot from the voice channel',
    )
    async def leave(self, interaction: discord.Interaction) -> None:
        """Have the bot leave the channel."""
        log_interaction(interaction)

    @app_commands.command(name='list', description='List available sounds')
    async def list(self, interaction: discord.Interaction) -> None:
        """List available sounds."""
        log_interaction(interaction)

    @app_commands.command(name='info', description='Information about a sound')
    @app_commands.describe(name='Name of sound to query')
    # TODO: autocomplete, list options
    async def info(self, interaction: discord.Interaction, name: str) -> None:
        """Information about a sound."""
        log_interaction(interaction)

    @app_commands.command(name='play', description='Play a sound')
    @app_commands.describe(name='Name of sound to play')
    # TODO: autocomplete, list options
    async def play(self, interaction: discord.Interaction, name: str) -> None:
        """Play a sound."""
        log_interaction(interaction)

        # TODO: call function on main bot

    @app_commands.command(name='remove', description='Remove a sound')
    @app_commands.describe(name='Name of sound to remove')
    @app_commands.check(admin_or_owner)
    # TODO: autocomplete, list options
    async def remove(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Remove a sound."""
        log_interaction(interaction)

    # TODO: task that can be started by another client
    async def leave_on_empty(self, client: discord.Client) -> None:
        """Attach leave on empty task to client.

        This will periodically check if the client is in an empty voice
        channel and have the client leave.
        """
        ...
