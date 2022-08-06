from __future__ import annotations

import logging
import os
import pathlib
from collections.abc import Generator
from unittest import mock

import pytest
from discord import app_commands

from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.utils import extract
from threepseat.bot import Bot
from threepseat.ext.sounds.commands import SoundCommands


@pytest.fixture
def mockbot(
    tmp_path: pathlib.Path,
    mock_download,
) -> Generator[Bot, None, None]:
    db_file = os.path.join(tmp_path, 'data.db')
    data_path = os.path.join(tmp_path, 'data')
    sound_commands = SoundCommands(db_path=db_file, data_path=data_path)
    bot = Bot(sound_commands=sound_commands)
    with mock.patch.object(bot.tree, 'sync', mock.AsyncMock()):
        yield bot


@pytest.mark.asyncio
async def test_add_command(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'Added' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_add_command_failure(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await add_(
        sounds,
        interaction,
        name='invalid sound name',
        link='localhost',
        description='a sound',
    )

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'alphanumeric' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_autocomplete(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    interaction = MockInteraction(
        sounds.info,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    choices = await sounds.autocomplete(interaction, current='my')
    assert any(['mysound' in choice.name for choice in choices])

    choices = await sounds.autocomplete(interaction, current='missing')
    assert len(choices) == 0


@pytest.mark.asyncio
async def test_list_command(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)
    list_ = extract(sounds.list)

    interaction = MockInteraction(
        sounds.list,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await list_(sounds, interaction)

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'no sounds' in interaction.followup_message
    )

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    interaction = MockInteraction(
        sounds.list,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await list_(sounds, interaction)

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'mysound' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_info_command(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)
    info_ = extract(sounds.info)

    interaction = MockInteraction(
        sounds.info,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await info_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'does not exist' in interaction.response_message
    )

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    interaction = MockInteraction(
        sounds.info,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await info_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'mysound' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_play_command(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)
    play_ = extract(sounds.play)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    interaction = MockInteraction(
        sounds.play,
        user=MockMember('name', 1234, MockGuild('guild', 12345)),
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    with (
        mock.patch(
            'threepseat.ext.sounds.commands.play_sound',
            mock.AsyncMock(),
        ),
        mock.patch(
            'threepseat.ext.sounds.commands.voice_channel',
            mock.MagicMock(return_value=object()),
        ),
    ):
        await play_(sounds, interaction, name='mysound')

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'Played!' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_play_command_missing(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    play_ = extract(sounds.play)

    interaction = MockInteraction(
        sounds.play,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await play_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'does not exist' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_play_command_not_in_channel(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)
    play_ = extract(sounds.play)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    interaction = MockInteraction(
        sounds.play,
        user=MockMember('name', 1234, MockGuild('guild', 12345)),
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    with mock.patch(
        'threepseat.ext.sounds.commands.voice_channel',
        mock.MagicMock(return_value=None),
    ):
        await play_(sounds, interaction, name='mysound')

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'voice channel' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_play_command_error(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)
    play_ = extract(sounds.play)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    interaction = MockInteraction(
        sounds.play,
        user=MockMember('name', 1234, MockGuild('guild', 12345)),
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    with (
        mock.patch(
            'threepseat.ext.sounds.commands.play_sound',
            side_effect=Exception(),
        ),
        mock.patch(
            'threepseat.ext.sounds.commands.voice_channel',
            mock.MagicMock(return_value=object()),
        ),
    ):
        await play_(sounds, interaction, name='mysound')

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'Failed to play' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_remove_command_missing(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    remove_ = extract(sounds.remove)

    interaction = MockInteraction(
        sounds.remove,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await remove_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'does not exist' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_remove_command(mockbot: Bot) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None
    add_ = extract(sounds.add)
    info_ = extract(sounds.info)
    remove_ = extract(sounds.remove)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await add_(
        sounds,
        interaction,
        name='mysound',
        link='localhost',
        description='a sound',
    )

    interaction = MockInteraction(
        sounds.remove,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await remove_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Removed' in interaction.response_message
    )

    interaction = MockInteraction(
        sounds.info,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await info_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'does not exist' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_on_error(mockbot: Bot, caplog) -> None:
    sounds = mockbot.sound_commands
    assert sounds is not None

    interaction = MockInteraction(
        sounds.remove,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await sounds.on_error(
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
    await sounds.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any(['test1' in record.message for record in caplog.records])
