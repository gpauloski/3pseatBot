from __future__ import annotations

import logging
from collections.abc import Generator
from unittest import mock

import pytest
from discord import app_commands

from testing.asserts import assert_followed
from testing.asserts import assert_responded
from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.utils import extract
from threepseat.bot import Bot
from threepseat.ext.custom.commands import CustomCommands
from threepseat.ext.custom.data import CustomCommand


@pytest.fixture
def command_fixtures(
    tmp_file: str,
) -> Generator[tuple[Bot, CustomCommands], None, None]:
    cc = CustomCommands(tmp_file)
    bot = Bot(extensions=[cc])
    with mock.patch.object(bot.tree, 'sync', mock.AsyncMock()):
        yield bot, cc


async def test_create(command_fixtures: tuple[Bot, CustomCommands]) -> None:
    mockbot, custom = command_fixtures
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
    assert_followed(interaction, 'command1')


async def test_create_invalid_name(
    command_fixtures: tuple[Bot, CustomCommands],
) -> None:
    mockbot, custom = command_fixtures
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
    assert_responded(interaction, 'alphanumeric')


async def test_list(command_fixtures: tuple[Bot, CustomCommands]) -> None:
    mockbot, custom = command_fixtures
    list_ = extract(custom.list)

    interaction = MockInteraction(
        custom.list,
        user='calling-user',
        channel='mychannel',
        guild=MockGuild('myguild', 5678),
        client=mockbot,
    )

    await list_(custom, interaction)
    assert_responded(interaction, 'no custom commands')

    command = CustomCommand(
        name='mycommand',
        description='a command',
        body='this is my command',
        author_id=1234,
        guild_id=5678,
        creation_time=0,
    )
    custom.table.update(command)
    with mock.patch.object(
        mockbot,
        'get_guild',
        return_value=interaction.guild,
    ):
        await custom.post_init(mockbot)

    interaction = MockInteraction(
        custom.list,
        user='calling-user',
        channel='mychannel',
        guild=MockGuild('myguild', 5678),
        client=mockbot,
    )
    await list_(custom, interaction)
    assert_responded(interaction, 'mycommand')


async def test_remove(command_fixtures: tuple[Bot, CustomCommands]) -> None:
    mockbot, custom = command_fixtures
    remove_ = extract(custom.remove)

    command = CustomCommand(
        name='mycommand',
        description='a command',
        body='this is my command',
        author_id=1234,
        guild_id=5678,
        creation_time=0,
    )
    custom.table.update(command)

    interaction = MockInteraction(
        custom.remove,
        user='calling-user',
        channel='mychannel',
        guild=MockGuild('guild', 5678),
        client=mockbot,
    )

    await remove_(custom, interaction, 'mycommand')
    assert_followed(interaction, 'Removed')

    interaction = MockInteraction(
        custom.remove,
        user='calling-user',
        channel='mychannel',
        guild=MockGuild('guild', 5678),
        client=mockbot,
    )

    await remove_(custom, interaction, 'mycommand')
    assert_followed(interaction, 'does not exist')


async def test_on_error(
    command_fixtures: tuple[Bot, CustomCommands],
    caplog: pytest.LogCaptureFixture,
) -> None:
    mockbot, custom = command_fixtures

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
    message = assert_responded(interaction)
    assert 'test' in message.lower()

    # Should not raise error, just log it
    caplog.set_level(logging.ERROR)
    await custom.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any('test1' in record.message for record in caplog.records)


async def test_autocomplete(tmp_file: str) -> None:
    custom = CustomCommands(tmp_file)
    command = CustomCommand(
        name='mycommand',
        description='a command',
        body='this is my command',
        author_id=1234,
        guild_id=5678,
        creation_time=0,
    )
    custom.table.update(command)

    interaction = MockInteraction(
        None,  # type: ignore[arg-type]
        user='calling-user',
        guild=MockGuild('guild', 5678),
    )

    options = await custom.autocomplete(interaction, current='')
    assert len(options) == 1

    options = await custom.autocomplete(interaction, current='other')
    assert len(options) == 0

    interaction = MockInteraction(
        None,  # type: ignore[arg-type]
        user='calling-user',
        guild=MockGuild('guild', 42),
    )

    options = await custom.autocomplete(interaction, current='')
    assert len(options) == 0
