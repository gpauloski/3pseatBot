from __future__ import annotations

import asyncio
from collections.abc import Generator
from unittest import mock

import discord
import pytest

from testing.mock import MockChannel
from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockUser
from testing.utils import extract
from threepseat.reminders.commands import ReminderCommands
from threepseat.reminders.commands import ReminderTask
from threepseat.reminders.commands import ReminderTaskKey
from threepseat.reminders.commands import WARN_ON_LONG_DELAY
from threepseat.reminders.data import Reminder
from threepseat.reminders.data import ReminderType


REMINDER = Reminder(
    guild_id=1234,
    channel_id=5678,
    author_id=9012,
    creation_time=0,
    name='test',
    text='test message',
    delay_minutes=1,
)


@pytest.fixture
def reminders(tmp_file: str) -> Generator[ReminderCommands, None, None]:
    yield ReminderCommands(tmp_file)


@pytest.mark.asyncio
async def test_start_repeating_reminders(reminders) -> None:
    reminders.database.update(REMINDER._replace(name='a'))
    reminders.database.update(REMINDER._replace(name='b'))

    with mock.patch('discord.Client'):
        client = discord.Client()  # type: ignore
        client.guilds = [  # type: ignore
            MockGuild('guild', REMINDER.guild_id),
            MockGuild('guild', 42),
        ]
        reminders.start_repeating_reminders(client)

    assert len(reminders._tasks) == 2

    for key, value in list(reminders._tasks.items()):
        reminders.stop_reminder(key.guild_id, key.name)
        with pytest.raises(asyncio.CancelledError):
            await value.task._task


@pytest.mark.asyncio
async def test_start_stop_reminder(reminders) -> None:
    with mock.patch('discord.Client'):
        reminders.start_reminder(
            discord.Client(),  # type: ignore
            REMINDER,
            ReminderType.ONE_TIME,
        )
        # Task is already running so this should do nothing
        reminders.start_reminder(
            discord.Client(),  # type: ignore
            REMINDER,
            ReminderType.ONE_TIME,
        )
        assert len(reminders._tasks) == 1

    value = reminders._tasks[ReminderTaskKey(REMINDER.guild_id, REMINDER.name)]
    reminders.stop_reminder(REMINDER.guild_id, REMINDER.name)
    assert len(reminders._tasks) == 0
    with pytest.raises(asyncio.exceptions.CancelledError):
        await value.task._task

    # Should be idempotent
    reminders.stop_reminder(REMINDER.guild_id, REMINDER.name)


@pytest.mark.asyncio
async def test_autocomplete(reminders) -> None:
    interaction = MockInteraction(
        None,  # type: ignore
        user='calling-user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )
    assert len(await reminders.autocomplete(interaction, current='')) == 0

    with mock.patch('discord.Client'):
        reminders.start_reminder(
            discord.Client(),  # type: ignore
            REMINDER._replace(name='a'),
            ReminderType.ONE_TIME,
        )
        reminders.start_reminder(
            discord.Client(),  # type: ignore
            REMINDER._replace(name='b'),
            ReminderType.ONE_TIME,
        )
    assert len(await reminders.autocomplete(interaction, current='')) == 2
    assert len(await reminders.autocomplete(interaction, current='c')) == 0

    tasks = [value.task for value in reminders._tasks.values()]
    reminders.stop_reminder(REMINDER.guild_id, 'a')
    reminders.stop_reminder(REMINDER.guild_id, 'b')
    for task in tasks:
        with pytest.raises(asyncio.CancelledError):
            await task._task


@pytest.mark.asyncio
async def test_one_time_reminders_delete_themselves(reminders) -> None:
    with mock.patch(
        'threepseat.reminders.utils.send_text_reminder',
    ) as mock_send:
        client = MockClient(MockUser('user', 1234))
        guild = MockGuild('guild', 5678)
        channel = MockChannel('channel', 9012)
        client.get_guild = mock.MagicMock(return_value=guild)
        guild.get_channel = mock.MagicMock(  # type: ignore
            return_value=channel,
        )
        reminders.start_reminder(
            client,
            # Run in roughly 10 ms
            REMINDER._replace(name='a', delay_minutes=0.0001),  # type: ignore
            ReminderType.ONE_TIME,
        )
        reminders.start_reminder(
            client,
            REMINDER._replace(name='b', delay_minutes=0.0001),  # type: ignore
            ReminderType.REPEATING,
        )

        key_a = ReminderTaskKey(REMINDER.guild_id, 'a')
        key_b = ReminderTaskKey(REMINDER.guild_id, 'b')
        value_a = reminders._tasks[key_a]
        value_b = reminders._tasks[key_b]

        # Sleep for 50 ms to ensure task runs
        await asyncio.sleep(0.05)

        assert key_a not in reminders._tasks
        assert key_b in reminders._tasks
        reminders.stop_reminder(REMINDER.guild_id, 'b')

        assert mock_send.await_count >= 1

        await value_a.task._task
        with pytest.raises(asyncio.exceptions.CancelledError):
            await value_b.task._task


@pytest.mark.asyncio
async def test_create_one_time(reminders) -> None:
    create_ = extract(reminders.create)

    interaction = MockInteraction(
        reminders.create,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    with mock.patch.object(reminders, 'start_reminder'):
        await create_(
            reminders,
            interaction,
            ReminderType.ONE_TIME,
            REMINDER.name,
            REMINDER.text,
            MockChannel('channel', 42),
            REMINDER.delay_minutes,
        )

    assert reminders.database.get(REMINDER.guild_id, REMINDER.name) is None

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Created' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_create_repeating(reminders) -> None:
    create_ = extract(reminders.create)

    interaction = MockInteraction(
        reminders.create,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    with mock.patch.object(reminders, 'start_reminder'):
        await create_(
            reminders,
            interaction,
            ReminderType.REPEATING,
            REMINDER.name,
            REMINDER.text,
            MockChannel('channel', 42),
            REMINDER.delay_minutes,
        )

    assert reminders.database.get(REMINDER.guild_id, REMINDER.name) is not None

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Created' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_create_alphanumeric_check(reminders) -> None:
    create_ = extract(reminders.create)

    interaction = MockInteraction(
        reminders.create,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    with mock.patch.object(reminders, 'start_reminder'):
        await create_(
            reminders,
            interaction,
            ReminderType.REPEATING,
            'not alphanumeric',
            REMINDER.text,
            MockChannel('channel', 42),
            REMINDER.delay_minutes,
        )

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'alphanumeric' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_create_name_exists(reminders) -> None:
    create_ = extract(reminders.create)

    interaction = MockInteraction(
        reminders.create,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    key = ReminderTaskKey(REMINDER.guild_id, REMINDER.name)
    reminders._tasks[key] = None
    with mock.patch.object(reminders, 'start_reminder'):
        await create_(
            reminders,
            interaction,
            ReminderType.REPEATING,
            REMINDER.name,
            REMINDER.text,
            MockChannel('channel', 42),
            REMINDER.delay_minutes,
        )

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'already exists' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_create_one_time_warn_long_delay(reminders) -> None:
    create_ = extract(reminders.create)

    interaction = MockInteraction(
        reminders.create,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    with mock.patch.object(reminders, 'start_reminder'):
        await create_(
            reminders,
            interaction,
            ReminderType.ONE_TIME,
            REMINDER.name,
            REMINDER.text,
            MockChannel('channel', 42),
            WARN_ON_LONG_DELAY + 1,
        )

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'long delays may be lost' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_info(reminders) -> None:
    info_ = extract(reminders.info)

    key = ReminderTaskKey(REMINDER.guild_id, REMINDER.name)
    value = ReminderTask(ReminderType.ONE_TIME, REMINDER, None)
    reminders._tasks[key] = value

    interaction = MockInteraction(
        reminders.info,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    with (
        mock.patch.object(interaction.client, 'get_user', return_value=None),
        mock.patch.object(interaction.guild, 'get_channel', return_value=None),
    ):
        await info_(reminders, interaction, REMINDER.name)

    assert interaction.responded
    assert interaction.response_message is not None
    assert REMINDER.name in interaction.response_message
    assert REMINDER.text in interaction.response_message
    assert ReminderType.ONE_TIME.value in interaction.response_message


@pytest.mark.asyncio
async def test_info_empty(reminders) -> None:
    info_ = extract(reminders.info)

    interaction = MockInteraction(
        reminders.info,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    await info_(reminders, interaction, REMINDER.name)

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'does not exist' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_list(reminders) -> None:
    list_ = extract(reminders.list)

    key = ReminderTaskKey(REMINDER.guild_id, 'a')
    value = ReminderTask(
        ReminderType.ONE_TIME,
        REMINDER._replace(name='a'),
        None,
    )
    reminders._tasks[key] = value

    key = ReminderTaskKey(REMINDER.guild_id, 'b')
    value = ReminderTask(
        ReminderType.ONE_TIME,
        REMINDER._replace(name='b'),
        None,
    )
    reminders._tasks[key] = value

    interaction = MockInteraction(
        reminders.list,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    with mock.patch.object(
        interaction.guild,
        'get_channel',
        return_value=None,
    ):
        await list_(reminders, interaction)

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'a:' in interaction.response_message
    assert 'b:' in interaction.response_message


@pytest.mark.asyncio
async def test_list_empty(reminders) -> None:
    list_ = extract(reminders.list)

    interaction = MockInteraction(
        reminders.list,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    await list_(reminders, interaction)

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'no reminders' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_remove(reminders) -> None:
    remove_ = extract(reminders.remove)

    interaction = MockInteraction(
        reminders.remove,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    key = ReminderTaskKey(REMINDER.guild_id, REMINDER.name)
    value = ReminderTask(
        ReminderType.ONE_TIME,
        REMINDER,
        mock.MagicMock(),
    )
    reminders._tasks[key] = value

    assert key in reminders._tasks
    await remove_(reminders, interaction, REMINDER.name)
    assert key not in reminders._tasks

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Removed' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_remove_missing(reminders) -> None:
    remove_ = extract(reminders.remove)

    interaction = MockInteraction(
        reminders.remove,
        user='user',
        guild=MockGuild('guild', REMINDER.guild_id),
    )

    await remove_(reminders, interaction, REMINDER.name)

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'does not exist' in interaction.response_message
    )
