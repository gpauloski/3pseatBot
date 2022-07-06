from __future__ import annotations

import logging
from typing import Generator
from unittest import mock

import pytest
from discord import app_commands

from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.utils import extract
from threepseat.bot import Bot
from threepseat.commands.custom import CustomCommand
from threepseat.commands.custom import CustomCommands


@pytest.fixture
def mockbot(tmp_file: str) -> Generator[Bot, None, None]:
    cc = CustomCommands(tmp_file)
    bot = Bot(custom_commands=cc)
    with mock.patch.object(bot.tree, 'sync', mock.AsyncMock()):
        yield bot


@pytest.mark.asyncio
async def test_create(mockbot: Bot) -> None:
    custom = mockbot.custom_commands
    assert custom is not None
    create_ = extract(custom.create)

    interaction = MockInteraction(
        custom.create,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    with mock.patch.object(
        mockbot,
        'get_guild',
        return_value=interaction.guild,
    ):
        await create_(
            custom,
            interaction,
            'command1',
            'description',
            'this is command 1',
        )
    assert interaction.followed
    assert interaction.followup_message is not None


@pytest.mark.asyncio
async def test_create_invalid_name(mockbot: Bot) -> None:
    custom = mockbot.custom_commands
    assert custom is not None
    create_ = extract(custom.create)

    interaction = MockInteraction(
        custom.create,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await create_(
        custom,
        interaction,
        'a a',
        'description',
        'this command has a bad name',
    )
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'alphanumeric' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_list(mockbot: Bot) -> None:
    custom = mockbot.custom_commands
    assert custom is not None
    list_ = extract(custom.list)

    interaction = MockInteraction(
        custom.list,
        user='calling-user',
        channel='mychannel',
        guild=MockGuild('myguild', 5678),
        client=mockbot,
    )

    await list_(custom, interaction)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'no custom commands' in interaction.response_message
    )

    command = CustomCommand(
        name='mycommand',
        description='a command',
        body='this is my command',
        author_id=1234,
        guild_id=5678,
        creation_time=0,
    )
    custom.add_to_db(command)
    with mock.patch.object(
        mockbot,
        'get_guild',
        return_value=interaction.guild,
    ):
        await custom.register_all(mockbot)

    interaction = MockInteraction(
        custom.list,
        user='calling-user',
        channel='mychannel',
        guild=MockGuild('myguild', 5678),
        client=mockbot,
    )
    await list_(custom, interaction)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'mycommand' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_remove(mockbot: Bot) -> None:
    custom = mockbot.custom_commands
    assert custom is not None
    remove_ = extract(custom.remove)

    interaction = MockInteraction(
        custom.remove,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await remove_(custom, interaction, 'command1')
    assert interaction.followed
    assert interaction.followup_message is not None


@pytest.mark.asyncio
async def test_on_error(mockbot: Bot, caplog) -> None:
    custom = mockbot.custom_commands
    assert custom is not None

    interaction = MockInteraction(
        custom.remove,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await custom.on_error(
        interaction,
        app_commands.MissingPermissions(['test']),
    )
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'test' in interaction.response_message.lower()
    )

    # Should not raise error, just log it
    caplog.set_level(logging.ERROR)
    await custom.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any(['test1' in record.message for record in caplog.records])


def test_db_create_command(tmp_file: str) -> None:
    custom = CustomCommands(tmp_file)
    command = CustomCommand(
        name='mycommand',
        description='a command',
        body='this is my command',
        author_id=1234,
        guild_id=5678,
        creation_time=0,
    )
    custom.add_to_db(command)

    with custom.connect() as db:
        rows = db.execute(
            'SELECT * FROM custom_commands WHERE name = :name',
            {'name': command.name},
        ).fetchall()
    assert len(rows) == 1


def test_db_list_commands(tmp_file: str) -> None:
    custom = CustomCommands(tmp_file)
    commands = [
        CustomCommand(
            name='mycommand1',
            description='a command',
            body='this is my command',
            author_id=1234,
            guild_id=1,
            creation_time=0,
        ),
        CustomCommand(
            name='mycommand2',
            description='a command',
            body='this is my command',
            author_id=1234,
            guild_id=1,
            creation_time=0,
        ),
        CustomCommand(
            name='mycommand3',
            description='a command',
            body='this is my command',
            author_id=1234,
            guild_id=2,
            creation_time=0,
        ),
    ]
    for command in commands:
        custom.add_to_db(command)

    found = custom.list_in_db(guild_id=1)
    assert len(found) == 2
    assert commands[0] in found
    assert commands[1] in found


def test_db_remove_command(tmp_file: str) -> None:
    custom = CustomCommands(tmp_file)
    command = CustomCommand(
        name='mycommand',
        description='a command',
        body='this is my command',
        author_id=1234,
        guild_id=5678,
        creation_time=0,
    )
    custom.add_to_db(command)

    with custom.connect() as db:
        rows = db.execute(
            'SELECT * FROM custom_commands WHERE name = :name',
            {'name': command.name},
        ).fetchall()
    assert len(rows) == 1

    custom.remove_from_db(command.name, command.guild_id)
    with custom.connect() as db:
        rows = db.execute(
            'SELECT * FROM custom_commands WHERE name = :name',
            {'name': command.name},
        ).fetchall()
    assert len(rows) == 0
