from __future__ import annotations

import asyncio
import random
import re
from typing import cast

import discord
from discord import app_commands
from emoji import emojize

from threepseat.commands.commands import log_interaction
from threepseat.commands.commands import register_app_command


@register_app_command
@app_commands.command(description='Roll for a random guild emote')
@app_commands.describe(match='Only roll for emotes that match this string')
@app_commands.check(log_interaction)
@app_commands.guild_only()
async def emote(interaction: discord.Interaction, match: str = '') -> None:
    """Roll an emote command."""
    await interaction.response.defer(thinking=True)

    assert interaction.guild is not None
    emotes = await interaction.guild.fetch_emojis()

    if len(emotes) == 0:
        await interaction.followup.send(
            f'This guild has no custom emotes {emojize(":disappointed:")}.',
        )
        return

    emotes = [
        emote for emote in emotes if re.search(f'(?i){match}', emote.name)
    ]

    if len(emotes) == 0:
        await interaction.followup.send(f'No guild emotes match "{match}".')
        return

    die = emojize(':game_die:')
    message = cast(
        discord.webhook.WebhookMessage,
        await interaction.followup.send(die),
    )
    for _ in range(4):
        await asyncio.sleep(0.1)
        await message.edit(content=str(random.choice(emotes)))
        await asyncio.sleep(0.1)
        await message.edit(content=die)
    await message.edit(content=str(random.choice(emotes)))
