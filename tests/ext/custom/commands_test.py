from __future__ import annotations

import logging
from collections.abc import Generator
from unittest import mock

import pytest
from discord import app_commands

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


@pytest.mark.asyncio
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
    assert interaction.followed
    assert interaction.followup_message is not None


@pytest.mark.asyncio
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
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'alphanumeric' in interaction.response_message
    )


@pytest.mark.asyncio
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
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'mycommand' in interaction.response_message
    )


@pytest.mark.asyncio
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
    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'Removed' in interaction.followup_message
    )

    interaction = MockInteraction(
        custom.remove,
        user='calling-user',
        channel='mychannel',
        guild=MockGuild('guild', 5678),
        client=mockbot,
    )

    await remove_(custom, interaction, 'mycommand')
    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'does not exist' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_on_error(
    command_fixtures: tuple[Bot, CustomCommands],
    caplog,
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
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'test' in interaction.response_message.lower()
    )

    # Should not raise error, just log it
    caplog.set_level(logging.ERROR)
    await custom.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any(['test1' in record.message for record in caplog.records])


@pytest.mark.asyncio
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
        None,  # type: ignore
        user='calling-user',
        guild=MockGuild('guild', 5678),
    )

    options = await custom.autocomplete(interaction, current='')
    assert len(options) == 1

    options = await custom.autocomplete(interaction, current='other')
    assert len(options) == 0

    interaction = MockInteraction(
        None,  # type: ignore
        user='calling-user',
        guild=MockGuild('guild', 42),
    )

    options = await custom.autocomplete(interaction, current='')
    assert len(options) == 0
