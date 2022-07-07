from __future__ import annotations

import functools
import io
import logging
import re
import warnings

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


def voice_channel(member: discord.Member) -> discord.VoiceChannel | None:
    """Get current voice channel of a member."""
    if member.voice is None or member.voice.channel is None:
        return None
    if isinstance(member.voice.channel, discord.VoiceChannel):
        return member.voice.channel
    return None


async def play_sound(sound: io.BytesIO, channel: discord.VoiceChannel) -> None:
    """Play a sound in the voice channel."""
    voice_client: discord.VoiceClient = await channel.connect()

    source = discord.FFmpegPCMAudio(sound, pipe=True)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        voice_client.play(source, after=None)


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
