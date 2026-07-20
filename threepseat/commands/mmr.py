from __future__ import annotations

import asyncio
import collections
import enum
import functools
import logging
import time
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from http import HTTPStatus
from typing import NamedTuple
from typing import cast

import discord
import requests
from discord import app_commands

from threepseat.commands.commands import log_interaction
from threepseat.logging import log_timing
from threepseat.utils import split_strings

logger = logging.getLogger(__name__)

DequeMaker = Callable[[], collections.deque[str]]

# Recently queried summoner lists, used to populate autocomplete. Keyed by
# guild, channel, or user ID (see cache_add): these are all Discord
# snowflakes, drawn from one ID space, so entries of different kinds cannot
# collide. Bounded per key by the deque's maxlen, but the dict itself grows
# with the number of distinct IDs that have used /mmr.
caches: dict[int, collections.deque[str]] = collections.defaultdict(
    cast('DequeMaker', functools.partial(collections.deque, maxlen=10)),
)

API_URL = 'https://na.whatismymmr.com/api/v1/summoner'
SUMMONER_NOT_FOUND_CODE = 101


class GameMode(enum.Enum):
    """Game mode options."""

    ARAM = 'ARAM'
    NORMAL = 'normal'
    RANKED = 'ranked'


class Stats(NamedTuple):
    """Stats returned by whatismymmr.com."""

    summoner: str
    status: Status
    gamemode: GameMode
    mmr: int = 0
    err: int = 0
    percentile: float = 0
    rank: str = ''
    time: int = 0


class Status(enum.Enum):
    """Status of MMR query."""

    AVAILABLE = 1
    UNAVAILABLE = 2
    UNKNOWN = 3
    ERROR = 4


def days_since(target: int, current: int | None = None) -> int:
    """Compute days since a target unix timestamp.

    Args:
        target (int): target unix timestamp.
        current (int, optional): specify the end timestamp otherwise
            defaults to the current time (default: None).

    Returns:
        integer days between `target` and `current`.
    """
    target_dt = datetime.fromtimestamp(target, tz=UTC)
    current_dt = datetime.fromtimestamp(
        current if current is not None else time.time(),
        tz=UTC,
    )
    diff = current_dt - target_dt
    return diff.days


def get_stats(summoner: str, gamemode: GameMode) -> Stats:
    """Query whatismymmr.com to get MMR stats for the summoner and gamemode.

    Args:
        summoner (str): name of summoner.
        gamemode (GameMode): gamemode to query MMR for.

    Returns:
        `Stats` object where the status attribute indicates if the
        query was successful or not.

    Raises:
        requests.RequestException:
            if the request to the external API fails (e.g. timeout or
            connection error).
    """
    try:
        with log_timing(
            logger,
            'queried MMR API for summoner %s (%s)',
            summoner,
            gamemode.value,
        ):
            result = requests.get(
                API_URL,
                params={'name': summoner},
                timeout=10,
            )
    except requests.RequestException:
        logger.exception(
            'request to %s failed for summoner %s',
            API_URL,
            summoner,
        )
        raise

    if result.status_code == HTTPStatus.NOT_FOUND:
        if (
            'error' in result.json()
            and result.json()['error']['code'] == SUMMONER_NOT_FOUND_CODE
        ):
            return Stats(
                summoner=summoner,
                status=Status.UNAVAILABLE,
                gamemode=gamemode,
            )
        return Stats(
            summoner=summoner,
            status=Status.UNKNOWN,
            gamemode=gamemode,
        )
    if result.status_code != HTTPStatus.OK:
        logger.warning(
            '%s returned %s for summoner %s.',
            API_URL,
            result.status_code,
            summoner,
        )
        return Stats(summoner=summoner, status=Status.ERROR, gamemode=gamemode)
    if result.json()[gamemode.value]['avg'] is None:
        return Stats(
            summoner=summoner,
            status=Status.UNAVAILABLE,
            gamemode=gamemode,
        )
    data = result.json()[gamemode.value]
    return Stats(
        summoner=summoner,
        status=Status.AVAILABLE,
        gamemode=gamemode,
        mmr=data['avg'],
        err=data['err'],
        percentile=data['percentile'],
        rank=data['closestRank'],
        time=data['timestamp'],
    )


def cache_add(
    item: str,
    guild: discord.Guild | None,
    channel: discord.interactions.InteractionChannel | None,
    user: discord.User | discord.Member,
) -> None:
    """Add item to cache.

    Preference is to first try adding to guild cache, then channel cache, and
    defaulting to user cache if neither of the previous exist. Sharing one
    dict across the three is safe because Discord IDs are snowflakes from a
    single ID space. autocomplete_summoners() must resolve the key the same
    way to read back what is written here.
    """
    if guild is not None:
        cache = caches[guild.id]
    elif channel is not None:
        cache = caches[channel.id]
    else:
        cache = caches[user.id]
    if item in cache:
        cache.remove(item)
    cache.appendleft(item)


async def autocomplete_summoners(
    interaction: discord.Interaction[discord.Client],
    current: str,
) -> list[app_commands.Choice[str]]:
    """Return items in cache matching current."""
    if interaction.guild is not None:
        cache = caches[interaction.guild.id]
    elif interaction.channel is not None:
        cache = caches[interaction.channel.id]
    else:
        cache = caches[interaction.user.id]
    return [
        app_commands.Choice(name=item, value=item)
        for item in cache
        if current.lower() in item.lower() or current == ''
    ]


@app_commands.command(description='Check League of Legends MMR')
@app_commands.describe(
    summoners='Comma separated list of summoner names',
    gamemode='Gamemode to check MMR for (default: ARAM)',
)
@app_commands.autocomplete(summoners=autocomplete_summoners)
@app_commands.check(log_interaction)
async def mmr(
    interaction: discord.Interaction[discord.Client],
    summoners: str,
    gamemode: GameMode = GameMode.ARAM,
) -> None:
    """MMR command."""
    await interaction.response.defer(thinking=True)

    sum_names = sorted(split_strings(summoners, delimiter=','))
    sum_stats: list[Stats] = []
    for summoner in sum_names:
        # get_stats() makes a blocking HTTP request with a 10 second timeout,
        # so keep it off the event loop.
        stats = await asyncio.to_thread(get_stats, summoner, gamemode)
        if stats.status == Status.ERROR:
            await interaction.followup.send('Unknown API error.')
            return
        if stats.status == Status.UNKNOWN:
            await interaction.followup.send(
                f'Summoner `{summoner}` does not exist in the NA server.',
            )
            return
        sum_stats.append(stats)

    # At this point no critical errors so we will save input to cache
    # for future autocomplete
    cache_add(
        ', '.join(sum_names),
        guild=interaction.guild,
        channel=interaction.channel,
        user=interaction.user,
    )

    available_sums = [x for x in sum_stats if x.status == Status.AVAILABLE]
    unavailable_sums = [x for x in sum_stats if x.status == Status.UNAVAILABLE]
    available_sums.sort(key=lambda s: s.mmr, reverse=True)
    unavailable_sums.sort(key=lambda s: s.summoner)

    f = '{name:<13} | {mmr:<4} {err:<5} | {rank:<21} | {days}'
    s = [
        'Summoner      | MMR        | Rank                  | Updated',
        '--------------|----------- | --------------------- | -----------',
    ]
    s.extend(
        f.format(
            name=stats.summoner[:13],
            mmr=stats.mmr,
            err=f'\u00b1 {stats.err}',
            rank=f'{stats.percentile}% / {stats.rank}',
            days=f'{days_since(stats.time)} days ago',
        )
        for stats in available_sums
    )
    s.extend(
        f.format(
            name=stats.summoner[:13],
            mmr='N/A',
            err='',
            rank='N/A',
            days='',
        )
        for stats in unavailable_sums
    )
    output = '\n'.join(s)

    await interaction.followup.send(
        f'MMR ({gamemode.value.lower()}) stats on the NA server:\n'
        f'```\n{output}\n```',
    )
