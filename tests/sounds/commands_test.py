from __future__ import annotations

import os
import pathlib
from typing import Generator
from unittest import mock

import pytest

from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.utils import extract
from threepseat.bot import Bot
from threepseat.sounds.commands import SoundCommands
from threepseat.sounds.data import Sounds


@pytest.fixture
def mockbot(
    tmp_path: pathlib.Path,
    mock_download,
) -> Generator[Bot, None, None]:
    db_file = os.path.join(tmp_path, 'data.db')
    data_path = os.path.join(tmp_path, 'data')
    sounds = Sounds(db_path=db_file, data_path=data_path)
    sound_commands = SoundCommands(sounds)
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
        mock.patch('threepseat.sounds.commands.play_sound', mock.AsyncMock()),
        mock.patch(
            'threepseat.sounds.commands.voice_channel',
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
        'threepseat.sounds.commands.voice_channel',
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
            'threepseat.sounds.commands.play_sound',
            side_effect=Exception(),
        ),
        mock.patch(
            'threepseat.sounds.commands.voice_channel',
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
        and 'Removed' in interaction.response_message
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
