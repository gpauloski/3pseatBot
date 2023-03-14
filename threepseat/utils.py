from __future__ import annotations

import asyncio
import datetime
import functools
import io
import logging
import re
import warnings
from collections.abc import Callable
from collections.abc import Coroutine
from collections.abc import Sequence
from typing import Any
from typing import cast

import discord
import discord.ext.tasks as tasks

logger = logging.getLogger(__name__)

LF = Callable[..., Coroutine[Any, Any, Any]]
LoopType = tasks.Loop[LF]


def alphanumeric(s: str) -> bool:
    """Check if string is alphanumeric characters only."""
    return len(re.findall(r'[^A-Za-z0-9]', s)) == 0


@functools.lru_cache(maxsize=16)
def cached_load(filepath: str) -> io.BytesIO:
    """Load file as bytes (cached)."""
    with open(filepath, 'rb') as f:
        return io.BytesIO(f.read())


def split_strings(text: str, delimiter: str = ',') -> list[str]:
    """Get non-empty parts in string list.

    Args:
        text (str): text to split.
        delimiter (str): delimiter to split using.

    Returns:
        list of stripped substrings.
    """
    parts = text.split(delimiter)
    parts = [part.strip() for part in parts]
    return [part for part in parts if len(part) > 0]


def primary_channel(guild: discord.Guild) -> discord.TextChannel | None:
    """Get the primary text channel for a guild."""
    if guild.system_channel is not None:
        return guild.system_channel

    for channel_candidate in guild.channels:
        if (
            isinstance(channel_candidate, discord.TextChannel)
            and channel_candidate.permissions_for(guild.me).send_messages
        ):
            return channel_candidate

    return None


def readable_sequence(values: Sequence[str], conjunction: str = 'and') -> str:
    """Joins a sequence as a readable list with commands and a conjunction.

    Args:
        values (sequence[str]): sequence of strings to join.
        conjunction (str): conjunction to join the last two elements by
            (default: and).

    Returns:
        string that is the joined sequence.
    """
    if len(values) == 0:
        return ''
    elif len(values) == 1:
        return values[0]
    elif len(values) == 2:
        return f'{values[0]} {conjunction} {values[1]}'

    before = ', '.join(values[:-1])
    after = values[-1]
    return f'{before}, {conjunction} {after}'


def readable_timedelta(
    *,
    days: float = 0,
    hours: float = 0,
    minutes: float = 0,
    seconds: float = 0,
) -> str:
    """Converts timedelta to readable string.

    Usage:
        >>> readable_timedelta(hours=12, minutes=3)
        "12 hours and 3 minutes"
        >>> readable_timedelta(days=2, hours=25, seconds=2)
        "3 days, 1 hour, and 2 seconds"
        >>> readable_timedelta()
        "0 seconds"

    Note:
        All arguments are passed to datetime.timedelta() and second is
        the lowest precision supported.

    Args:
        days (float): number of days (default: 0).
        hours (float): number of hours (default: 0).
        minutes (float): number of minutes (default: 0).
        seconds (float): number of seconds (default: 0).

    Returns:
        time delta formatted as readable string.
    """
    delta = datetime.timedelta(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )
    remainder = int(delta.total_seconds())

    days, remainder = divmod(remainder, 60 * 60 * 24)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, remainder = divmod(remainder, 60)
    seconds = remainder

    units: list[tuple[int, str]] = []
    if days != 0:
        units.append((days, 'day' if days == 1 else 'days'))
    if hours != 0:
        units.append((hours, 'hour' if hours == 1 else 'hours'))
    if minutes != 0:
        units.append((minutes, 'minute' if minutes == 1 else 'minutes'))
    if seconds != 0:
        units.append((seconds, 'second' if seconds == 1 else 'seconds'))

    if len(units) == 0:
        return '0 seconds'

    units_ = [f'{value} {unit}' for value, unit in units]
    return readable_sequence(units_, 'and')


def voice_channel(member: discord.Member) -> discord.VoiceChannel | None:
    """Get current voice channel of a member."""
    if member.voice is None or member.voice.channel is None:
        return None
    if isinstance(member.voice.channel, discord.VoiceChannel):
        return member.voice.channel
    return None


async def play_sound(
    sound: str,
    channel: discord.VoiceChannel,
    wait: bool = False,
) -> None:
    """Play a sound in the voice channel.

    Args:
        sound (filepath): filepath to MP3 file to play.
        channel (discord.VoiceChannel): voice channel to play sound in.
        wait (bool): wait for sound to finish playing before exiting. Otherwise
            the coroutine may return before the sound has finished.
    """
    voice_client: discord.VoiceClient
    if channel.guild.voice_client is not None:
        await channel.guild.voice_client.move_to(channel)  # type: ignore
        voice_client = cast(discord.VoiceClient, channel.guild.voice_client)
    else:
        voice_client = await channel.connect()

    source = discord.FFmpegPCMAudio(sound)

    if voice_client.is_playing():
        voice_client.stop()

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        voice_client.play(source, after=None)

    if wait:
        while voice_client.is_playing():
            await asyncio.sleep(0.1)


def leave_on_empty(
    client: discord.Client,
    interval: float = 30,
) -> LoopType:
    """Returns a task that when started will leave empty voice channels.

    This will periodically check if the client is in an empty voice
    channel and have the client leave.

    Usage:
        >>> checker = leave_on_empty(bot, 30)
        >>> checker.start()

    Args:
        client (Client): client to check for active voice channels.
        interval (float): time in seconds between checking.

    Returns:
        discord.ext.tasks.Loop
    """

    @tasks.loop(seconds=interval)
    async def _leaver() -> None:
        for voice_client in client.voice_clients:
            if (
                isinstance(voice_client, discord.VoiceClient)
                and len(voice_client.channel.members) <= 1
            ):
                logger.info(
                    f'leaving voice channel {voice_client.channel.name} in '
                    f'{voice_client.channel.guild.name} due to inactivity',
                )
                await voice_client.disconnect()

    return _leaver
