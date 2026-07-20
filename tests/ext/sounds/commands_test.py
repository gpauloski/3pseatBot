from __future__ import annotations

import logging
import pathlib
from collections.abc import Generator
from unittest import mock

import discord
import pytest
from discord import app_commands

from testing.asserts import assert_followed
from testing.asserts import assert_responded
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

    assert_followed(interaction, 'Added')


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

    assert_followed(interaction, 'Name must')
    assert mock_download.call_count == 0


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

    assert_followed(interaction, 'already exists')


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

    assert_followed(interaction, 'Error downloading sound.')


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

    assert_followed(interaction, 'no sounds')

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

    assert_followed(interaction, 'mysound')


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

    assert_responded(interaction, 'does not exist')

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

    assert_responded(interaction, 'mysound')


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

    assert_followed(interaction, 'Played!')


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

    assert_responded(interaction, 'does not exist')


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

    assert_followed(interaction, 'voice channel')


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

    assert_followed(interaction, 'Failed to play')


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

    assert_responded(interaction, 'does not exist')


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

    assert_responded(interaction, 'Removed')

    interaction = MockInteraction(
        sounds.info,
        user='calling-user',
        channel='mychannel',
        guild='myguild',
        client=mockbot,
    )
    await info_(sounds, interaction, name='mysound')

    assert_responded(interaction, 'does not exist')


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

    assert_followed(interaction, 'Uploaded and added')


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

    assert_followed(interaction, 'must be an MP3')


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

    assert_followed(interaction, 'Name must')


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

    assert_followed(interaction, 'File size must be under')


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

    assert_followed(interaction, 'Sound is too long')


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

    assert_followed(interaction, 'Could not process the file')


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

    assert_followed(interaction, 'Could not process the file')


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

    assert_followed(interaction, 'Uploaded and added')


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

    assert_followed(interaction, 'supported video')


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

    assert_followed(interaction, 'File size must be under')


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

    assert_followed(interaction, 'Sound is too long')


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

    assert_followed(interaction, 'Could not process the file')


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
    message = assert_responded(interaction)
    assert 'test' in message.lower()

    # Should not raise error, just log it
    caplog.set_level(logging.ERROR)
    await sounds.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any('test1' in record.message for record in caplog.records)


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

    caplog.set_level(logging.ERROR)
    with mock.patch(
        'threepseat.ext.sounds.commands.play_sound',
        side_effect=Exception(),
    ):
        # exception should be captured and logged
        await sounds.on_voice_state_update(member, before, after)

    assert any('exception' in record.message for record in caplog.records)


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

    assert_responded(interaction, 'does not exist')


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

    assert_responded(interaction, 'Updated your voice channel entry')
