from __future__ import annotations

import asyncio
import functools
import io
import logging
import re
import warnings
from typing import cast

import discord
import discord.ext.tasks as tasks

logger = logging.getLogger(__name__)


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
        delimiter (str): delimter to split using.

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
) -> tasks.Loop[tasks.LF]:
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
