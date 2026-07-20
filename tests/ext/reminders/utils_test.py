from __future__ import annotations

import logging
from unittest import mock

from testing.data import REMINDER as SHARED_REMINDER
from testing.mock import MockChannel
from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockMember
from testing.mock import MockUser
from testing.mock import MockVoiceChannel
from testing.utils import wait_for
from threepseat.ext.reminders.data import ReminderType
from threepseat.ext.reminders.utils import reminder_task
from threepseat.ext.reminders.utils import send_text_reminder
from threepseat.ext.reminders.utils import send_voice_reminder

# Run in roughly 10 ms rather than a minute.
REMINDER = SHARED_REMINDER._replace(delay_minutes=0.0001)  # type: ignore[arg-type]


async def test_reminder_task() -> None:
    with (
        mock.patch(
            'threepseat.ext.reminders.utils.send_text_reminder',
        ) as mock_text,
        mock.patch(
            'threepseat.ext.reminders.utils.send_voice_reminder',
        ) as mock_voice,
    ):
        client = MockClient(MockUser('user', 1234))
        guild = MockGuild('guild', 5678)
        text_channel = MockChannel('channel', 9012)
        voice_channel = MockVoiceChannel()
        client.get_guild = mock.MagicMock(  # type: ignore[method-assign]
            return_value=guild,
        )

        guild.get_channel = mock.MagicMock(  # type: ignore[method-assign]
            return_value=text_channel,
        )
        task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
        task.start()
        await wait_for(lambda: mock_text.await_count == 1)
        task.cancel()

        guild.get_channel = mock.MagicMock(  # type: ignore[method-assign]
            return_value=voice_channel,
        )
        task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
        task.start()
        await wait_for(lambda: mock_voice.await_count == 1)
        task.cancel()


async def test_reminder_task_missing_guild(caplog) -> None:
    caplog.set_level(logging.ERROR)
    client = MockClient(MockUser('user', 1234))
    client.get_guild = mock.MagicMock(  # type: ignore[method-assign]
        return_value=None,
    )

    task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
    task.start()
    await wait_for(
        lambda: any('find guild' in r.message for r in caplog.records),
    )
    task.cancel()


async def test_reminder_task_missing_channel(caplog) -> None:
    caplog.set_level(logging.ERROR)
    client = MockClient(MockUser('user', 1234))
    guild = MockGuild('guild', 5678)
    client.get_guild = mock.MagicMock(  # type: ignore[method-assign]
        return_value=guild,
    )
    guild.get_channel = mock.MagicMock(  # type: ignore[method-assign]
        return_value=None,
    )

    task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, None)
    task.start()
    await wait_for(
        lambda: any('find text/voice' in r.message for r in caplog.records),
    )
    task.cancel()


async def test_reminder_task_callback() -> None:
    with mock.patch(
        'threepseat.ext.reminders.utils.send_text_reminder',
    ) as mock_text:
        client = MockClient(MockUser('user', 1234))
        guild = MockGuild('guild', 5678)
        text_channel = MockChannel('channel', 9012)
        client.get_guild = mock.MagicMock(  # type: ignore[method-assign]
            return_value=guild,
        )

        guild.get_channel = mock.MagicMock(  # type: ignore[method-assign]
            return_value=text_channel,
        )

        callback = mock.MagicMock()
        task = reminder_task(client, REMINDER, ReminderType.ONE_TIME, callback)
        task.start()
        await wait_for(lambda: mock_text.await_count > 0)
        task.cancel()
        assert callback.called


async def test_send_text_reminder() -> None:
    channel = MockChannel('channel')
    message = 'test message'

    with mock.patch.object(channel, 'send') as mock_send:
        await send_text_reminder(channel, message)
        assert mock_send.await_count == 1


async def test_send_voice_reminder_skips_empty_channels() -> None:
    client = MockClient(MockUser('user', 1234))
    channel = MockVoiceChannel()
    message = 'test message'

    with (
        mock.patch('threepseat.tts.gTTS'),
        mock.patch('threepseat.ext.reminders.utils.play_sound') as mock_play,
    ):
        await send_voice_reminder(client, channel, message)
        assert mock_play.await_count == 0


async def test_send_voice_reminder() -> None:
    client = MockClient(MockUser('user', 1234))
    channel = MockVoiceChannel()
    message = 'test message'

    channel._members = [MockMember('user', 42, MockGuild('guild', 1234))]

    with (
        mock.patch('threepseat.tts.gTTS'),
        mock.patch('threepseat.ext.reminders.utils.play_sound') as mock_play,
    ):
        await send_voice_reminder(client, channel, message)
        assert mock_play.await_count == 1
