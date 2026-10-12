from __future__ import annotations

import asyncio
import datetime
import random

import discord
from discord import app_commands
from emoji import emojize

from threepseat.commands.commands import log_interaction


@app_commands.command(
    description='Poll who wants to join an Idle Clans clan event',
)
@app_commands.describe(event='event details (e.g., "Griffin 10x")')
@app_commands.describe(spots='spots for other members, not counting you')
@app_commands.describe(minutes='minutes to wait for entries (default: 3)')
@app_commands.check(log_interaction)
@app_commands.guild_only()
async def clan(
    interaction: discord.Interaction[discord.Client],
    event: str,
    spots: app_commands.Range[int, 1, 25],
    minutes: app_commands.Range[int, 1, 60] = 3,
) -> list[discord.User | discord.Member]:
    """Poll members to join a clan event and pick who enters."""
    invoker = interaction.user

    header = f'{invoker.mention} is starting an event: **{event}**'
    plural = spots != 1
    available = f'**{spots} {"spots" if plural else "spot"} available**'
    end = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)

    await interaction.response.send_message(
        f'{header}\n\n'
        f'There {"are" if plural else "is"} {available}. '
        f'Entries close {discord.utils.format_dt(end, "R")}. '
        'React to enter the random drawing for participants.',
    )
    message = await interaction.original_response()
    emoji = emojize(':saluting_face:')
    await message.add_reaction(emoji)

    await asyncio.sleep(minutes * 60)

    # original_response() is cached and the bot lacks the reactions intent,
    # so re-fetch the message to see the current reactions.
    fetched = await message.fetch()
    entrants: dict[int, discord.User | discord.Member] = {}
    for reaction in fetched.reactions:
        async for user in reaction.users():
            if user.bot or user.id == invoker.id:
                continue
            entrants.setdefault(user.id, user)

    candidates = list(entrants.values())
    selected = (
        random.sample(candidates, spots)
        if len(candidates) > spots
        else candidates
    )
    mentions = _join([user.mention for user in selected])

    # Relative timestamps keep counting into the past, so replace it.
    # Edits do not send mention notifications so a followup is still needed.
    result = f'Selected: {mentions}.' if selected else 'No one entered.'
    await interaction.edit_original_response(
        content=(
            f'{header}\n\n'
            f'There {"were" if plural else "was"} {available}. '
            f'Entries closed at {discord.utils.format_dt(end, "f")}. '
            f'{result}'
        ),
    )
    if interaction.client.user is not None:
        await message.remove_reaction(emoji, interaction.client.user)

    if not selected:
        await interaction.followup.send(
            f'No one entered the drawing for **{event}**, {invoker.mention}.',
        )
        return []

    verb = 'was' if len(selected) == 1 else 'were'
    await interaction.followup.send(
        f'{mentions} {verb} selected for **{event}** '
        f'hosted by {invoker.mention}.',
    )

    return selected


def _join(items: list[str]) -> str:
    if len(items) <= 2:  # noqa: PLR2004
        return ' and '.join(items)
    return f'{", ".join(items[:-1])}, and {items[-1]}'
