from __future__ import annotations

import logging
import pathlib
from collections.abc import Generator
from unittest import mock

import discord
import pytest
from discord import app_commands

from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.mock import MockVoiceChannel
from testing.utils import extract
from threepseat.bot import Bot
from threepseat.ext.sounds.commands import SoundCommands
from threepseat.ext.sounds.data import MAX_SOUND_FILE_SIZE_BYTES
from threepseat.ext.sounds.data import MAX_SOUND_LENGTH_SECONDS
from threepseat.ext.sounds.data import MAX_VIDEO_FILE_SIZE_BYTES
from threepseat.ext.sounds.data import MemberSound
from threepseat.ext.sounds.data import Sound


@pytest.fixture
def sound_fixtures(
    tmp_path: pathlib.Path,
    mock_download,  # noqa: ARG001 (requested for its side effect)
) -> Generator[tuple[Bot, SoundCommands], None, None]:
    db_file = str(tmp_path / 'data.db')
    data_path = str(tmp_path / 'data')
    sound_commands = SoundCommands(db_path=db_file, data_path=data_path)
    bot = Bot(extensions=[sound_commands])
    with mock.patch.object(bot.tree, 'sync', mock.AsyncMock()):
        yield bot, sound_commands


def create_mock_attachment(
    filename: str = 'test_sound.mp3',
    size: int = 1024,
    content: bytes = b'dummy_mp3_data',
) -> mock.AsyncMock:
    attachment = mock.AsyncMock(spec=discord.Attachment)
    attachment.filename = filename
    attachment.size = size
    attachment.read.return_value = content
    return attachment


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
    assert interaction.followup_message is not None
    assert 'Added' in interaction.followup_message


@pytest.mark.asyncio
async def test_add_command_invalid_name(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    # A '../' name would escape the sounds directory, so it must be rejected
    # before download() writes anything.
    mockbot, sounds = sound_fixtures
    add_ = extract(sounds.add)

    interaction = MockInteraction(
        sounds.add,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    with mock.patch(
        'threepseat.ext.sounds.commands.download',
    ) as mock_download:
        await add_(
            sounds,
            interaction,
            name='../../evil',
            link='localhost',
            description='a sound',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Name must' in interaction.followup_message
    assert mock_download.call_count == 0


@pytest.mark.asyncio
async def test_add_command_exists(
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

    with mock.patch.object(sounds.table, 'get', return_value=True):
        await add_(
            sounds,
            interaction,
            name='name',
            link='localhost',
            description='a sound',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'already exists' in interaction.followup_message


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

    with mock.patch(
        'threepseat.ext.sounds.commands.download',
        side_effect=ValueError('Error downloading sound.'),
    ):
        await add_(
            sounds,
            interaction,
            name='mysound',
            link='localhost',
            description='a sound',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Error downloading sound.' in interaction.followup_message


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
    assert any('mysound' in choice.name for choice in choices)

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
    assert interaction.followup_message is not None
    assert 'no sounds' in interaction.followup_message

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
    assert interaction.followup_message is not None
    assert 'mysound' in interaction.followup_message


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
    assert interaction.response_message is not None
    assert 'does not exist' in interaction.response_message

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
    assert interaction.response_message is not None
    assert 'mysound' in interaction.response_message


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
    assert interaction.followup_message is not None
    assert 'Played!' in interaction.followup_message


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
    assert interaction.response_message is not None
    assert 'does not exist' in interaction.response_message


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
    assert interaction.followup_message is not None
    assert 'voice channel' in interaction.followup_message


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
    assert interaction.followup_message is not None
    assert 'Failed to play' in interaction.followup_message


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
    assert interaction.response_message is not None
    assert 'does not exist' in interaction.response_message


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
    assert interaction.response_message is not None
    assert 'Removed' in interaction.response_message

    interaction = MockInteraction(
        sounds.info,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await info_(sounds, interaction, name='mysound')

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'does not exist' in interaction.response_message


@pytest.mark.asyncio
async def test_upload_command_success(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    with mock.patch(
        'threepseat.ext.sounds.data.mp3_duration_seconds',
        return_value=15.0,
    ):
        await upload_(
            sounds,
            interaction,
            file=create_mock_attachment(),
            name='uploaded',
            description='a fresh sound',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Uploaded and added' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_invalid_extension(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await upload_(
        sounds,
        interaction,
        file=create_mock_attachment(filename='test.wav'),
        name='badext',
        description='should fail extension check',
    )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'must be an MP3' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_invalid_name(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    # The name becomes part of the filename, so it is validated before the
    # upload is written anywhere.
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await upload_(
        sounds,
        interaction,
        file=create_mock_attachment(filename='test.mp3'),
        name='../../evil',
        description='should fail name check',
    )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Name must' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_file_too_large(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await upload_(
        sounds,
        interaction,
        file=create_mock_attachment(size=2 * MAX_SOUND_FILE_SIZE_BYTES),
        name='toobig',
        description='should fail size check',
    )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'File size must be under' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_duration_too_long(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    with mock.patch(
        'threepseat.ext.sounds.data.mp3_duration_seconds',
        return_value=2 * MAX_SOUND_LENGTH_SECONDS,
    ):
        await upload_(
            sounds,
            interaction,
            file=create_mock_attachment(),
            name='toolong',
            description='should fail duration check',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Sound is too long' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_duration_extraction_error(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    with mock.patch(
        'threepseat.ext.sounds.data.mp3_duration_seconds',
        side_effect=Exception('FFmpeg error'),
    ):
        await upload_(
            sounds,
            interaction,
            file=create_mock_attachment(),
            name='corrupt',
            description='should handle parsing exceptions gracefully',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Could not process the file' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_write_disk_error(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    # Force a write error when saving the file to disk
    with (
        mock.patch(
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            return_value=10.0,
        ),
        mock.patch(
            'pathlib.Path.write_bytes',
            side_effect=OSError('Disk Full or Permission Denied'),
        ),
    ):
        await upload_(
            sounds,
            interaction,
            file=create_mock_attachment(),
            name='diskerror',
            description='should fail gracefully on file save',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Could not process the file' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_video_success(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    # Emulate extraction by creating the destination MP3 so table.add finds it.
    async def fake_extract(_source, mp3_path) -> None:
        pathlib.Path(mp3_path).touch()

    with (
        mock.patch(
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            return_value=1.0,
        ),
        mock.patch(
            'threepseat.ext.sounds.data.extract_audio',
            side_effect=fake_extract,
        ),
    ):
        await upload_(
            sounds,
            interaction,
            file=create_mock_attachment(filename='clip.mp4'),
            name='fromvideo',
            description='a video sound',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Uploaded and added' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_unsupported_type(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await upload_(
        sounds,
        interaction,
        file=create_mock_attachment(filename='clip.mkv'),
        name='badtype',
        description='unsupported container',
    )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'supported video' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_video_too_large(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    await upload_(
        sounds,
        interaction,
        file=create_mock_attachment(
            filename='clip.mp4',
            size=2 * MAX_VIDEO_FILE_SIZE_BYTES,
        ),
        name='bigvideo',
        description='should fail size check',
    )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'File size must be under' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_video_too_long(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    with mock.patch(
        'threepseat.ext.sounds.data.mp3_duration_seconds',
        return_value=2 * MAX_SOUND_LENGTH_SECONDS,
    ):
        await upload_(
            sounds,
            interaction,
            file=create_mock_attachment(filename='clip.mov'),
            name='longvideo',
            description='should fail duration check',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Sound is too long' in interaction.followup_message


@pytest.mark.asyncio
async def test_upload_command_video_extract_error(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures
    upload_ = extract(sounds.upload)

    interaction = MockInteraction(
        sounds.upload,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )

    with (
        mock.patch(
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            return_value=1.0,
        ),
        mock.patch(
            'threepseat.ext.sounds.data.extract_audio',
            side_effect=RuntimeError('ffmpeg blew up'),
        ),
    ):
        await upload_(
            sounds,
            interaction,
            file=create_mock_attachment(filename='clip.mp4'),
            name='badvideo',
            description='should handle extraction failures',
        )

    assert interaction.followed
    assert interaction.followup_message is not None
    assert 'Could not process the file' in interaction.followup_message


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
    assert interaction.response_message is not None
    assert 'test' in interaction.response_message.lower()

    # Should not raise error, just log it
    caplog.set_level(logging.ERROR)
    await sounds.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any('test1' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_post_init(
    sound_fixtures: tuple[Bot, SoundCommands],
) -> None:
    mockbot, sounds = sound_fixtures

    with mock.patch.object(mockbot, 'add_listener'):
        await sounds.post_init(mockbot)
    assert sounds._vc_leaver_task is not None

    await sounds.post_shutdown()
    assert sounds._vc_leaver_task is None
    assert sounds.table._db is None
    assert sounds.join_table._db is None


@pytest.mark.asyncio
async def test_voice_state_update(
    sound_fixtures: tuple[Bot, SoundCommands],
    caplog,
) -> None:
    _, sounds = sound_fixtures

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
        sound = Sound.new(
            name='test',
            description='test',
            link='https://youtube.com',
            author_id=2,
            guild_id=1,
        )
        with mock.patch('pathlib.Path.is_file', return_value=True):
            sounds.table.add(sound)
        await sounds.on_voice_state_update(member, before, after)
        assert mock_play.await_count == 1

    with mock.patch(
        'threepseat.ext.sounds.commands.play_sound',
        side_effect=Exception(),
    ):
        # exception should be captured and logged
        await sounds.on_voice_state_update(member, before, after)

    caplog.set_level(logging.ERROR)
    assert any('exception' in record.message for record in caplog.records)


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
    assert interaction.response_message is not None
    assert 'does not exist' in interaction.response_message


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

    sound = Sound.new(
        name='mysound',
        description='test',
        link='https://youtube.com',
        author_id=interaction.user.id,
        guild_id=interaction.guild.id,
    )
    with mock.patch('pathlib.Path.is_file', return_value=True):
        sounds.table.add(sound)
    assert len(sounds.join_table.all(interaction.guild.id)) == 0
    await register_(sounds, interaction, name='mysound')
    assert len(sounds.join_table.all(interaction.guild.id)) == 1

    assert interaction.response
    assert interaction.response_message is not None
    assert 'Updated your voice channel entry' in interaction.response_message
