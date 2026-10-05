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

    header = f'{invoker.mention} is starting an event: {event}'
    plural = spots != 1
    end = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)

    await interaction.response.send_message(
        f'{header}\n\n'
        f'There {"are" if plural else "is"} {spots} '
        f'{"spots" if plural else "spot"} available. '
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
    status = (
        f'Entries closed. Selected: {mentions}.'
        if selected
        else 'Entries closed. No one entered.'
    )
    await interaction.edit_original_response(content=f'{header}\n\n{status}')
    if interaction.client.user is not None:
        await message.remove_reaction(emoji, interaction.client.user)

    if not selected:
        await interaction.followup.send(
            f'No one entered the drawing for {message.jump_url}, '
            f'{invoker.mention}.',
        )
        return []

    verb = 'was' if len(selected) == 1 else 'were'
    if len(candidates) > spots:
        detail = f'from {len(candidates)} entrants'
    else:
        noun = 'spot' if spots == 1 else 'spots'
        detail = f'({len(selected)} of {spots} {noun} filled)'
    await interaction.followup.send(
        f'Drawing results for {message.jump_url}: {mentions} {verb} '
        f'selected {detail}. Hosted by {invoker.mention}.',
    )

    return selected


def _join(items: list[str]) -> str:
    if len(items) <= 2:  # noqa: PLR2004
        return ' and '.join(items)
    return f'{", ".join(items[:-1])}, and {items[-1]}'
