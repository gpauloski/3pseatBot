from __future__ import annotations

import asyncio
import logging
from unittest import mock

import pytest

from testing.mock import MockChannel
from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockMember
from testing.mock import MockUser
from testing.mock import MockVoiceChannel
from threepseat.reminders.data import Reminder
from threepseat.reminders.data import ReminderType
from threepseat.reminders.utils import reminder_task
from threepseat.reminders.utils import send_text_reminder
from threepseat.reminders.utils import send_voice_reminder

REMINDER = Reminder(
    guild_id=1234,
    channel_id=5678,
    author_id=9012,
    creation_time=0,
    name='test',
    text='test message',
    delay_minutes=0.0001,  # type: ignore
)


@pytest.mark.asyncio
async def test_reminder_task() -> None:
    with (
        mock.patch(
            'threepseat.reminders.utils.send_text_reminder',
        ) as mock_text,
        mock.patch(
            'threepseat.reminders.utils.send_voice_reminder',
        ) as mock_voice,
    ):
        client = MockClient(MockUser('user', 1234))
        guild = MockGuild('guild', 5678)
        text_channel = MockChannel('channel', 9012)
        voice_channel = MockVoiceChannel()
        client.get_guild = mock.MagicMock(return_value=guild)

        guild.get_channel = mock.MagicMock(  # type: ignore
            return_value=text_channel,
        )
        task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
        task.start()
        await asyncio.sleep(0.02)
        assert mock_text.await_count == 1
        task.cancel()

        guild.get_channel = mock.MagicMock(  # type: ignore
            return_value=voice_channel,
        )
        task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
        task.start()
        await asyncio.sleep(0.02)
        assert mock_voice.await_count == 1
        task.cancel()


@pytest.mark.asyncio
async def test_reminder_task_missing_guild(caplog) -> None:
    caplog.set_level(logging.ERROR)
    client = MockClient(MockUser('user', 1234))
    client.get_guild = mock.MagicMock(return_value=None)

    task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
    task.start()
    await asyncio.sleep(0.02)
    task.cancel()

    assert any(['find guild' in record.message for record in caplog.records])


@pytest.mark.asyncio
async def test_reminder_task_missing_channel(caplog) -> None:
    caplog.set_level(logging.ERROR)
    client = MockClient(MockUser('user', 1234))
    guild = MockGuild('guild', 5678)
    client.get_guild = mock.MagicMock(return_value=guild)
    guild.get_channel = mock.MagicMock(return_value=None)  # type: ignore

    task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
    task.start()
    await asyncio.sleep(0.02)
    task.cancel()

    assert any(
        ['find text/voice' in record.message for record in caplog.records],
    )


@pytest.mark.asyncio
async def test_reminder_task_callback() -> None:
    with mock.patch(
        'threepseat.reminders.utils.send_text_reminder',
    ) as mock_text:
        client = MockClient(MockUser('user', 1234))
        guild = MockGuild('guild', 5678)
        text_channel = MockChannel('channel', 9012)
        client.get_guild = mock.MagicMock(return_value=guild)

        guild.get_channel = mock.MagicMock(  # type: ignore
            return_value=text_channel,
        )

        callback = mock.MagicMock()
        task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, callback)
        task.start()
        await asyncio.sleep(0.02)
        assert mock_text.await_count == 1
        task.cancel()
        assert callback.called


@pytest.mark.asyncio
async def test_send_text_reminder() -> None:
    channel = MockChannel('channel')
    message = 'test message'

    with mock.patch.object(channel, 'send') as mock_send:
        await send_text_reminder(channel, message)
        assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_send_voice_reminder() -> None:
    client = MockClient(MockUser('user', 1234))
    channel = MockVoiceChannel()
    message = 'test message'

    with (
        mock.patch('threepseat.tts.gTTS'),
        mock.patch('threepseat.reminders.utils.play_sound') as mock_play,
    ):
        await send_voice_reminder(client, channel, message)
        assert mock_play.await_count == 0


@pytest.mark.asyncio
async def test_send_voice_reminder_skips_empty_channels() -> None:
    client = MockClient(MockUser('user', 1234))
    channel = MockVoiceChannel()
    message = 'test message'

    channel._members = [MockMember('user', 42, MockGuild('guild', 1234))]

    with (
        mock.patch('threepseat.tts.gTTS'),
        mock.patch('threepseat.reminders.utils.play_sound') as mock_play,
    ):
        await send_voice_reminder(client, channel, message)
        assert mock_play.await_count == 1
