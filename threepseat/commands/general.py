from __future__ import annotations

import random
from typing import cast
from typing import Literal

import discord
from discord import app_commands

import threepseat
from threepseat.commands.commands import log_interaction
from threepseat.commands.commands import register


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


@register
@app_commands.command(description='3pseatBot source code')
async def source(interaction: discord.Interaction) -> None:
    """Get 3pseatBot's source code link."""
    log_interaction(interaction)
    name = (
        'Bot'
        if interaction.client.user is None
        else interaction.client.user.name
    )
    await interaction.response.send_message(
        f'This is {name} v{threepseat.__version__}. '
        f'You can find source code at https://github.com/gpauloski/3pseatBot.',
    )
