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
from testing.mock import MockVoiceChannel
from testing.utils import extract
from threepseat.bot import Bot
from threepseat.ext.sounds.commands import SoundCommands
from threepseat.ext.sounds.data import MemberSound


@pytest.fixture
def sound_fixtures(
    tmp_path: pathlib.Path,
    mock_download,
) -> Generator[tuple[Bot, SoundCommands], None, None]:
    db_file = os.path.join(tmp_path, 'data.db')
    data_path = os.path.join(tmp_path, 'data')
    sound_commands = SoundCommands(db_path=db_file, data_path=data_path)
    bot = Bot(extensions=[sound_commands])
    with mock.patch.object(bot.tree, 'sync', mock.AsyncMock()):
        yield bot, sound_commands


@pytest.mark.asyncio
async def test_add_command(sound_fixtures: tuple[Bot, SoundCommands]) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_add_command_failure(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_autocomplete(sound_fixtures: tuple[Bot, SoundCommands]) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_list_command(sound_fixtures: tuple[Bot, SoundCommands]) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_info_command(sound_fixtures: tuple[Bot, SoundCommands]) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_play_command(sound_fixtures: tuple[Bot, SoundCommands]) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_play_command_missing(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_play_command_not_in_channel(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_play_command_error(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_remove_command_missing(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_remove_command(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
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
async def test_on_error(
    sound_fixtures: tuple[Bot, SoundCommands],
    caplog,
) -> None:
    mockbot, sounds = sound_fixtures

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


@pytest.mark.asyncio
async def test_post_init(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures

    with mock.patch.object(mockbot, 'add_listener'):
        await sounds.post_init(mockbot)
    sounds._vc_leaver_task.cancel()


@pytest.mark.asyncio
async def test_voice_state_update(
    sound_fixtures: tuple[Bot, SoundCommands],
    caplog,
) -> None:
    mockbot, sounds = sound_fixtures

    guild = MockGuild('guild', 1)
    member = MockMember('member', 2, guild)

    before = mock.MagicMock()
    after = mock.MagicMock()
    before.channel = None
    after.channel = None

    with mock.patch('threepseat.ext.sounds.commands.play_sound') as mock_play:
        # skip: before and after are the same
        await sounds.on_voice_state_update(member, before, after)
        assert mock_play.await_count == 0

        # skip: after channel is not voice channel
        before.channel = MockVoiceChannel()
        await sounds.on_voice_state_update(member, before, after)
        assert mock_play.await_count == 0

        # skip: member has not registered sound
        after.channel = before.channel
        before.channel = None
        await sounds.on_voice_state_update(member, before, after)
        assert mock_play.await_count == 0

        # skip: sound is not in database
        sounds.join_table.update(
            MemberSound(member_id=2, guild_id=1, name='test', updated_time=0),
        )
        await sounds.on_voice_state_update(member, before, after)
        assert mock_play.await_count == 0

        # succeed
        sounds.table.add(
            name='test',
            description='test',
            link='https://youtube.com',
            author_id=2,
            guild_id=1,
        )
        await sounds.on_voice_state_update(member, before, after)
        assert mock_play.await_count == 1

    with mock.patch(
        'threepseat.ext.sounds.commands.play_sound',
        side_effect=Exception(),
    ):
        # exception should be captured and logged
        await sounds.on_voice_state_update(member, before, after)

    caplog.set_level(logging.ERROR)
    assert any(['exception' in record.message for record in caplog.records])


@pytest.mark.asyncio
async def test_register_command_sound_missing(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    register_ = extract(sounds.register)

    interaction = MockInteraction(
        sounds.register,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await register_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'does not exist' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_register_command(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    register_ = extract(sounds.register)

    interaction = MockInteraction(
        sounds.register,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    assert interaction.guild is not None
    assert interaction.user is not None

    sounds.table.add(
        name='mysound',
        description='test',
        link='https://youtube.com',
        author_id=interaction.user.id,
        guild_id=interaction.guild.id,
    )
    assert len(sounds.join_table.all(interaction.guild.id)) == 0
    await register_(sounds, interaction, name='mysound')
    assert len(sounds.join_table.all(interaction.guild.id)) == 1

    assert interaction.response
    assert (
        interaction.response_message is not None
        and 'Updated your voice channel entry' in interaction.response_message
    )
