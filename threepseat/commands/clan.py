from __future__ import annotations

import asyncio
import datetime
import random

import discord
from discord import app_commands
from emoji import emojize

from threepseat.commands.commands import log_interaction


@app_commands.command(
    description='Poll who wants to join an Idle Clans clan boss',
)
@app_commands.describe(boss='clan boss name')
@app_commands.describe(minutes='minutes to wait for entries (default: 1)')
@app_commands.describe(
    spots='spots for other members, not counting you (default: 2)',
)
@app_commands.describe(note='optional extra details (e.g., "running it 10x")')
@app_commands.check(log_interaction)
@app_commands.guild_only()
async def clan(
    interaction: discord.Interaction[discord.Client],
    boss: str,
    minutes: app_commands.Range[int, 1, 60] = 1,
    spots: app_commands.Range[int, 1, 25] = 2,
    note: str | None = None,
) -> list[discord.User | discord.Member]:
    """Poll members to join a clan boss and pick who enters."""
    invoker = interaction.user
    end = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)

    header = f'{invoker.mention} is doing **{boss}**!'
    footer = f'\n> {note}' if note else ''

    await interaction.response.send_message(
        f'{header} React to this message '
        f'{discord.utils.format_dt(end, "R")} to join '
        f'({spots} spots available).{footer}',
    )
    message = await interaction.original_response()
    await message.add_reaction(emojize(':saluting_face:'))

    await asyncio.sleep(minutes * 60)

    # Relative timestamps keep counting into the past, so replace it.
    await interaction.edit_original_response(
        content=f'{header} Sign-ups are closed.{footer}',
    )

    # original_response() is cached and the bot lacks the reactions intent,
    # so re-fetch the message to see the current reactions.
    fetched = await message.fetch()
    entrants: dict[int, discord.User | discord.Member] = {}
    for reaction in fetched.reactions:
        async for user in reaction.users():
            if user.bot or user.id == invoker.id:
                continue
            entrants.setdefault(user.id, user)

    if len(entrants) == 0:
        await interaction.followup.send(
            f'No one joined for **{boss}**, {invoker.mention}.',
        )
        return []

    candidates = list(entrants.values())
    selected = (
        random.sample(candidates, spots)
        if len(candidates) > spots
        else candidates
    )

    team = ', '.join(user.mention for user in (invoker, *selected))
    result = f'**{boss}** team: {team}'
    if len(candidates) > spots:
        result += f' (randomly picked {spots} of {len(candidates)})'
    await interaction.followup.send(result)

    return selected
