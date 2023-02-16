from __future__ import annotations

import logging
from typing import Any
from typing import TypeAlias
from typing import TypeVar

import discord
from discord import app_commands
from discord.app_commands.commands import Command as _Command
from discord.app_commands.commands import Group
from discord.ext import commands

Command: TypeAlias = _Command[Any, Any, Any]
CommandType = TypeVar('CommandType', Command, Group)

_app_commands: list[Command | Group] = []
logger = logging.getLogger(__name__)


def register_app_command(command: CommandType) -> CommandType:
    """Register the app command.

    Usage:
        >>> @register
        >>> @app_command.command()
        >>> def mycommand(interaction, ...): ...
    """
    _app_commands.append(command)
    return command


def registered_app_commands() -> list[Command | Group]:
    """Get list of registered application commands."""
    # Shallow copy here so caller does not mess up our list by accident
    return _app_commands[:]


def extract_command_options(
    interaction: discord.Interaction,
) -> dict[str, Any] | None:
    """Extract options from command interaction."""
    if interaction.data is None or 'options' not in interaction.data:
        return None
    options: dict[str, Any] = {}
    for option in interaction.data['options']:  # type: ignore[typeddict-item]
        if 'options' in option:
            for suboption in option['options']:  # type: ignore[typeddict-item]
                value = suboption['value']  # type: ignore[typeddict-item]
                options[suboption['name']] = value
        else:
            value = option['value']
            options[option['name']] = value
    return options


async def log_interaction(interaction: discord.Interaction) -> bool:
    """Log that an interaction occurred.

    Note:
        This is hacked as a command check that always succeeds.

    Usage:
        >>> @app_commands.command()
        >>> @app_commands.check(log_interaction)
        >>> def mycommand(...): ...
    """
    channel = interaction.channel
    channel_name = (
        None if not hasattr(channel, 'name') else channel.name  # type: ignore
    )
    channel_name = (
        channel_name
        if channel_name is not None
        else channel.id  # type: ignore
    )

    guild = None if interaction.guild is None else interaction.guild.name
    command = None if interaction.command is None else interaction.command.name
    options = extract_command_options(interaction)

    logger.info(
        f'[Channel: {channel_name}, Guild: {guild}] '
        f'{interaction.user.name} ({interaction.user.id}) called '
        f'/{command}: {options}',
    )

    return True


async def admin_or_owner(interaction: discord.Interaction) -> bool:
    """Check if invoker of interaction is the bot owner or guild admin.

    Usage:
        >>> @app_commands.command()
        >>> @app_commands.check(admin_or_owner)
        >>> def mycommand(...): ...
    """
    if isinstance(
        interaction.client,
        commands.Bot,
    ) and await interaction.client.is_owner(interaction.user):
        return True
    elif (
        isinstance(interaction.user, discord.Member)
        and interaction.user.guild_permissions.administrator
    ):
        return True
    else:
        raise app_commands.MissingPermissions(['admin'])
