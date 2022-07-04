from __future__ import annotations

import logging
import random
from typing import Any
from typing import cast
from typing import Literal
from typing import TypeAlias

import discord
from discord import app_commands
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
    message = (
        None
        if interaction.message is None
        else interaction.message.clean_content
    )

    logger.log(
        level,
        f'[Channel: {channel_name}, Guild: {guild}] '
        f'{interaction.user.name} ({interaction.user.id}) called '
        f'/{command}: {message}',
    )


@register
@app_commands.command(description='flip a coin')
@app_commands.describe(user='specify a user to flip for (defaults to self)')
async def flip(
    interaction: discord.Interaction,
    user: discord.Member | discord.User | None = None,
) -> Literal['heads', 'tails']:
    """Flip a coin."""
    log_interaction(interaction)
    result = ('heads', 'tails')[random.randint(0, 1)]

    if user is None:
        user = interaction.user

    await interaction.response.send_message(
        f'{user.mention} got ***{result}***!',
    )
    return cast(Literal['heads', 'tails'], result)


@register
@app_commands.command(description='roll a number in the range')
@app_commands.describe(start='min value in range')
@app_commands.describe(end='max value in range')
@app_commands.describe(user='specify a user to roll for (defaults to self)')
async def roll(
    interaction: discord.Interaction,
    start: int,
    end: int,
    user: discord.Member | discord.User | None = None,
) -> int:
    """Roll a number."""
    log_interaction(interaction)
    if start > end:
        start, end = end, start
    num = random.randint(start, end)

    if user is None:
        user = interaction.user

    await interaction.response.send_message(
        f'{user.mention} rolled **{num}** from [{start}, {end}]!',
    )
    return num
