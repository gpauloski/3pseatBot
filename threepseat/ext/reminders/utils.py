from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable

import discord
from discord.ext import tasks

from threepseat.ext.reminders.data import Reminder
from threepseat.ext.reminders.data import ReminderType
from threepseat.tts import Accent
from threepseat.tts import tts_as_mp3
from threepseat.utils import play_sound

logger = logging.getLogger(__name__)


def reminder_task(
    client: discord.Client,
    reminder: Reminder,
    kind: ReminderType,
    callback: Callable[[], None] | None,
) -> tasks.Loop[tasks.LF]:
    """Return task that periodically sends reminder.

    Usage:
        >>> task = reminder_task(bot, Reminder(...), ReminderType.REPEATING)
        >>> task.start()

    Args:
        client (Client): client/bot that performs reminders.
        reminder (Reminder): reminder configuration.
        kind (ReminderType): type of reminder to configure if tasks should
            only run once.
        callable (Callable): optional callable that takes no arguments that
            will be executed after the task is finished. Note this is really
            only relevant for one-time tasks.

    Returns:
        discord.ext.tasks.Loop
    """

    @tasks.loop(
        minutes=reminder.delay_minutes,
        # Note: count is 2 because we skip first loop
        count=2 if kind == ReminderType.ONE_TIME else None,
    )
    async def _reminder() -> None:
        if _reminder.current_loop == 0 and kind == ReminderType.ONE_TIME:
            # Skip first loop so task actually does delay before first
            # reminder. We only do this for one time reminders as repeating
            # reminders have a random sleep added before the first loop.
            return

        guild = client.get_guild(reminder.guild_id)
        if guild is None:
            logger.error(
                f'Failed to find guild {reminder.guild_id} for '
                f'reminder named {reminder.name}',
            )
            return

        channel = guild.get_channel(reminder.channel_id)
        if isinstance(channel, discord.TextChannel):
            await send_text_reminder(channel, reminder.text)
        elif isinstance(channel, discord.VoiceChannel):
            await send_voice_reminder(client, channel, reminder.text)
        else:
            logger.error(
                f'Failed to find text/voice channel with ID '
                f'{reminder.channel_id} in {guild.name} ({guild.id}) for '
                f'reminder named {reminder.name}',
            )
            return

        logger.info(
            f'reminder {reminder.name} run for guild {guild.name} '
            f'({guild.id}) in channel {channel.name} ({channel.id})',
        )

        if (
            _reminder.current_loop == 1
            and kind == ReminderType.ONE_TIME
            and callback is not None
        ):
            callback()

    @_reminder.before_loop
    async def _delay_start() -> None:
        # For repeating reminders, we start reminder at some random offset
        # for some /variation/
        if kind == ReminderType.REPEATING:
            offset_seconds = 60 * random.uniform(1, reminder.delay_minutes)
            await asyncio.sleep(int(offset_seconds))

    return _reminder


async def send_text_reminder(
    channel: discord.TextChannel,
    message: str,
) -> None:
    """Send message in text channel."""
    await channel.send(message)


async def send_voice_reminder(
    client: discord.Client,
    channel: discord.VoiceChannel,
    message: str,
) -> None:
    """Send message as TTS in voice channel."""
    client_id = -1 if client.user is None else client.user.id
    members = [m for m in channel.members if m.id != client_id]
    if len(members) == 0:
        return

    # Randomize voice
    accent = Accent.from_str('', random_if_unknown=True)
    slow = random.random() < 0.1

    with tts_as_mp3(message, accent=accent, slow=slow) as fp:
        await play_sound(fp, channel, wait=True)
