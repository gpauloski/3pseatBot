from __future__ import annotations

import logging
from typing import Any
from typing import TypeAlias

import discord
from discord.app_commands.commands import Command as _Command

Command: TypeAlias = _Command[Any, Any, Any]

_app_commands: list[Command] = []
logger = logging.getLogger(__name__)


def register(command: Command) -> Command:
    """Register the app command.

    Usage:
        >>> @register
        >>> @app_command.command()
        >>> def mycommand(interaction, ...): ...
    """
    _app_commands.append(command)
    return command


def registered_commands() -> list[Command]:
    """Get list of registered application commands."""
    # Shallow copy here so caller does not mess up our list by accident
    return _app_commands[:]


def log_interaction(
    interaction: discord.Interaction,
    level: int = logging.INFO,
) -> None:
    """Log that an interaction occurred."""
    channel = interaction.channel
    channel_name = (
        None if not hasattr(channel, 'name') else channel.name  # type: ignore
    )
    channel_name = (
        channel_name
        if not hasattr(channel, 'id')
        else channel.id  # type: ignore
    )

    guild = None if interaction.guild is None else interaction.guild.name
    command = (
        None
        if interaction.command is None
        else interaction.command.__class__.__name__
    )

    logger.log(
        level,
        f'[Channel: {channel_name}, Guild: {guild}] '
        f'{interaction.user.name} ({interaction.user.id}) called /{command}',
    )
