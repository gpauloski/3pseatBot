from __future__ import annotations

import datetime
from asyncio import sleep as asleep
from collections.abc import Generator
from unittest import mock

import discord
import pytest

from testing.mock import MockChannel
from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.utils import extract
from threepseat.ext.birthdays.commands import BirthdayCommands
from threepseat.ext.birthdays.commands import Months
from threepseat.ext.birthdays.data import Birthday


BIRTHDAY = Birthday(
    guild_id=1234,
    user_id=5678,
    author_id=9012,
    creation_time=0,
    birth_day=1,
    birth_month=2,
)


@pytest.fixture
def birthdays(tmp_file: str) -> Generator[BirthdayCommands, None, None]:
    yield BirthdayCommands(tmp_file)


@pytest.mark.asyncio
async def test_birthday_task(birthdays) -> None:
    with mock.patch('discord.Client'):
        client = discord.Client()  # type: ignore
        client.guilds = [MockGuild('guild', 42)]  # type: ignore

    with (
        mock.patch('asyncio.sleep'),
        mock.patch.object(birthdays, 'send_birthday_messages') as mock_send,
    ):
        task = birthdays.birthday_task(client)
        task.change_interval(seconds=0.01)
        task.start()
        while task.current_loop == 0:
            await asleep(0.005)
        task.cancel()

        assert mock_send.await_count >= 1


@pytest.mark.asyncio
async def test_birthday_task_sleeps_until_start(birthdays) -> None:
    from threepseat.ext.birthdays import commands

    with mock.patch('discord.Client'):
        client = discord.Client()  # type: ignore
        client.guilds = []  # type: ignore

    with mock.patch('asyncio.sleep'):
        # Force time to be in future
        commands.BIRTHDAY_CHECK_HOUR = 23
        commands.BIRTHDAY_CHECK_MINUTE = 59

        task = birthdays.birthday_task(client)
        task.change_interval(seconds=0.01)
        task.start()
        while task.current_loop == 0:
            await asleep(0.005)
        task.cancel()

        # Force time to be in past
        commands.BIRTHDAY_CHECK_HOUR = 0
        commands.BIRTHDAY_CHECK_MINUTE = 0

        task = birthdays.birthday_task(client)
        task.change_interval(seconds=0.01)
        task.start()
        while task.current_loop == 0:
            await asleep(0.005)
        task.cancel()


@pytest.mark.asyncio
async def test_send_birthday_messages(birthdays) -> None:
    guild = MockGuild('guild', BIRTHDAY.guild_id)
    channel = MockChannel('channel', 42)

    birthdays.table.update(BIRTHDAY._replace(user_id=1))
    birthdays.table.update(
        BIRTHDAY._replace(
            user_id=2,
            birth_month=datetime.datetime.now().month,
            birth_day=datetime.datetime.now().day,
        ),
    )
    birthdays.table.update(
        BIRTHDAY._replace(
            user_id=3,
            birth_month=datetime.datetime.now().month,
            birth_day=datetime.datetime.now().day,
        ),
    )
    member = MockMember('user', 2, guild)

    with (
        mock.patch.object(channel, 'send', mock.AsyncMock()) as mock_send,
        mock.patch.object(guild, 'get_member', side_effect=[member, None]),
        mock.patch(
            'threepseat.ext.birthdays.commands.primary_channel',
            return_value=channel,
        ),
    ):
        await birthdays.send_birthday_messages(guild)
        assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_send_birthday_messages_no_channel_found(birthdays) -> None:
    guild = MockGuild('guild', BIRTHDAY.guild_id)

    with mock.patch(
        'threepseat.ext.birthdays.commands.primary_channel',
        return_value=None,
    ):
        await birthdays.send_birthday_messages(guild)


@pytest.mark.asyncio
async def test_add_birthday(birthdays) -> None:
    add_ = extract(birthdays.add)

    guild = MockGuild('guild', BIRTHDAY.guild_id)
    interaction = MockInteraction(birthdays.add, user='user', guild=guild)

    await add_(
        birthdays,
        interaction,
        MockMember('user', 42, guild),
        Months(BIRTHDAY.birth_month),
        BIRTHDAY.birth_day,
    )

    birthday = birthdays.table.get(guild.id, 42)
    assert birthday is not None
    assert birthday.birth_month == BIRTHDAY.birth_month
    assert birthday.birth_day == BIRTHDAY.birth_day

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Added birthday' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_add_birthday_invalid_date(birthdays) -> None:
    add_ = extract(birthdays.add)

    guild = MockGuild('guild', BIRTHDAY.guild_id)
    interaction = MockInteraction(birthdays.add, user='user', guild=guild)

    await add_(
        birthdays,
        interaction,
        MockMember('user', 42, guild),
        Months.February,
        31,
    )

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Invalid birthday' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_list_birthdays(birthdays) -> None:
    list_ = extract(birthdays.list)

    guild = MockGuild('guild', BIRTHDAY.guild_id)
    interaction = MockInteraction(birthdays.list, user='user', guild=guild)

    birthdays.table.update(BIRTHDAY._replace(user_id=1))
    birthdays.table.update(BIRTHDAY._replace(user_id=2))
    birthdays.table.update(BIRTHDAY._replace(guild_id=0, user_id=1))

    # Mock second call to get_member to return None
    _members = [MockMember('user', 1, guild), None]

    with mock.patch.object(guild, 'get_member', side_effect=_members):
        await list_(birthdays, interaction)

    assert interaction.followed
    assert interaction.followup_message is not None
    # One output line because there are three rows, two in the guild we
    # query from, and one of the members in the guild will not be found
    assert len(interaction.followup_message.split('\n')) == 1


@pytest.mark.asyncio
async def test_list_birthdays_empty(birthdays) -> None:
    list_ = extract(birthdays.list)

    guild = MockGuild('guild', BIRTHDAY.guild_id)
    interaction = MockInteraction(birthdays.list, user='user', guild=guild)

    await list_(birthdays, interaction)

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'no birthdays' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_remove_birthday(birthdays) -> None:
    remove_ = extract(birthdays.remove)

    guild = MockGuild('guild', BIRTHDAY.guild_id)
    interaction = MockInteraction(birthdays.remove, user='user', guild=guild)

    birthdays.table.update(BIRTHDAY)

    await remove_(
        birthdays,
        interaction,
        MockMember('user', BIRTHDAY.user_id, guild),
    )

    assert birthdays.table.get(BIRTHDAY.guild_id, BIRTHDAY.user_id) is None
    assert interaction.responded
    assert interaction.response_message is not None
    assert 'Removed' in interaction.response_message


@pytest.mark.asyncio
async def test_remove_birthday_missing(birthdays) -> None:
    remove_ = extract(birthdays.remove)

    guild = MockGuild('guild', BIRTHDAY.guild_id)
    interaction = MockInteraction(birthdays.remove, user='user', guild=guild)

    await remove_(birthdays, interaction, MockMember('user', 42, guild))

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'birthday has not been added' in interaction.response_message
