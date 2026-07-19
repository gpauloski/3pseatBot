from __future__ import annotations

import os
import pathlib
import time
from unittest import mock

import pytest

from threepseat.ext.sounds.data import MemberSound
from threepseat.ext.sounds.data import MemberSoundTable
from threepseat.ext.sounds.data import Sound
from threepseat.ext.sounds.data import SoundsTable
from threepseat.ext.sounds.data import download
from threepseat.ext.sounds.data import extract_audio
from threepseat.ext.sounds.data import mp3_duration_seconds
from threepseat.ext.sounds.data import supported_video_extensions_str

TEST_SOUND = Sound.new(
    name='mysound',
    description='test sound',
    link='https://youtube.com/abcd',
    author_id=1234,
    guild_id=5678,
)


@pytest.fixture
def sounds(tmp_path: pathlib.Path) -> SoundsTable:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')

    sounds = SoundsTable(db_path=db_path, data_path=data_path)
    test_sound_path = pathlib.Path(sounds.filepath(TEST_SOUND.filename))
    test_sound_path.touch()

    return sounds


def test_filepath(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')
    filename = 'testfile.mp3'

    sounds = SoundsTable(db_path=db_path, data_path=data_path)
    assert not os.path.isdir(data_path)
    assert sounds.filepath(filename) == os.path.join(data_path, filename)
    assert os.path.isdir(data_path)


def test_add_get_sound(sounds: SoundsTable) -> None:
    sounds.add(TEST_SOUND)

    found = sounds.get(name=TEST_SOUND.name, guild_id=TEST_SOUND.guild_id)
    assert found is not None
    assert found.name == TEST_SOUND.name
    assert found.description == TEST_SOUND.description
    assert found.link == TEST_SOUND.link
    assert found.author_id == TEST_SOUND.author_id
    assert found.guild_id == TEST_SOUND.guild_id
    assert TEST_SOUND.name in found.filename
    assert str(TEST_SOUND.guild_id) in found.filename
    # Check creation time within last 5 seconds
    assert time.time() - found.created_time < 5


def test_add_sound_validation(sounds: SoundsTable) -> None:
    with pytest.raises(ValueError, match='alphanumeric'):
        sounds.add(TEST_SOUND._replace(name='my sound'))

    with pytest.raises(ValueError, match='alphanumeric'):
        sounds.add(TEST_SOUND._replace(name='mysound%'))

    with pytest.raises(ValueError, match='between'):
        sounds.add(TEST_SOUND._replace(name=''))

    with pytest.raises(ValueError, match='between'):
        sounds.add(TEST_SOUND._replace(name='x' * 32))

    with pytest.raises(ValueError, match='does not exist'):
        sounds.add(TEST_SOUND._replace(filename='foo.mp3'))


def test_add_sound_exists(sounds: SoundsTable) -> None:
    sounds.add(TEST_SOUND)

    with pytest.raises(ValueError, match='exists'):
        sounds.add(TEST_SOUND)


def test_all_sounds(sounds: SoundsTable) -> None:
    sounds_list = [
        dict(
            name='mysound1',
            description='test sound1',
            link='https://youtube.com/abcd1',
            author_id=1234,
            guild_id=5678,
        ),
        dict(
            name='mysound2',
            description='test sound2',
            link='https://youtube.com/abcd2',
            author_id=1234,
            guild_id=5678,
        ),
        dict(
            name='mysound3',
            description='test sound3',
            link='https://youtube.com/abcd3',
            author_id=1234,
            guild_id=0,
        ),
    ]

    for sound_data in sounds_list:
        sound = Sound.new(
            name=sound_data['name'],  # type: ignore[arg-type]
            description=sound_data['description'],  # type: ignore[arg-type]
            link=sound_data['link'],  # type: ignore[arg-type]
            author_id=sound_data['author_id'],  # type: ignore[arg-type]
            guild_id=sound_data['guild_id'],  # type: ignore[arg-type]
        )
        pathlib.Path(sounds.filepath(sound.filename)).touch()
        sounds.add(sound)

    assert len(sounds.all(guild_id=-1)) == 0
    assert len(sounds.all(guild_id=0)) == 1
    found = sounds.all(guild_id=5678)
    assert len(found) == 2

    names = {s.name for s in found}
    assert names == {'mysound1', 'mysound2'}


def test_remove_sound(sounds: SoundsTable) -> None:
    sounds.add(TEST_SOUND)

    found1 = sounds.get(name=TEST_SOUND.name, guild_id=TEST_SOUND.guild_id)
    assert found1 is not None
    assert os.path.exists(os.path.join(sounds.filepath(found1.filename)))

    sounds.remove(name=TEST_SOUND.name, guild_id=TEST_SOUND.guild_id)
    found2 = sounds.get(name=TEST_SOUND.name, guild_id=TEST_SOUND.guild_id)
    assert found2 is None
    assert not os.path.exists(os.path.join(sounds.filepath(found1.filename)))

    # Should not error if sound does not exist
    sounds.remove(name='notasound', guild_id=123456789)


def test_youtube_download(tmp_path: pathlib.Path) -> None:
    filepath = os.path.join(tmp_path, 'test_video.mp3')
    link = 'https://www.youtube.com/watch?v=jhFDyDgMVUI'

    with (
        mock.patch(
            'threepseat.ext.sounds.data.YoutubeDL.extract_info',
            return_value={'duration': 0.1},
        ),
        mock.patch('threepseat.ext.sounds.data.YoutubeDL.download'),
    ):
        download(link, filepath)


def test_youtube_download_errors(tmp_path: pathlib.Path) -> None:
    filepath = os.path.join(tmp_path, 'test_video.mp3')
    link = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    with mock.patch(
        'threepseat.ext.sounds.data.YoutubeDL.extract_info',
    ) as mock_extract:
        mock_extract.return_value = {'duration': 10000}
        with pytest.raises(ValueError, match='Clip is longer than'):
            download(link, filepath)

        mock_extract.return_value = {'duration': 0}
        with mock.patch(
            'threepseat.ext.sounds.data.YoutubeDL.extract_info',
            side_effect=Exception('test'),
        ):
            with pytest.raises(ValueError, match='extracting'):
                download(link, filepath)

        link = 'https://www.youtube.com/watch?v=jhFDyDgMVUI'
        with mock.patch(
            'threepseat.ext.sounds.data.YoutubeDL.download',
            side_effect=Exception('test'),
        ):
            with pytest.raises(
                ValueError,
                match='downloading',
            ):  # pragma: no branch
                download(link, filepath)


def _mock_ffprobe_process(
    *,
    returncode: int,
    stdout: bytes,
    stderr: bytes = b'',
) -> mock.MagicMock:
    proc = mock.MagicMock()
    proc.returncode = returncode
    proc.wait = mock.AsyncMock()
    proc.stdout = mock.MagicMock()
    proc.stdout.read = mock.AsyncMock(return_value=stdout)
    proc.stderr = mock.MagicMock()
    proc.stderr.read = mock.AsyncMock(return_value=stderr)
    return proc


@pytest.mark.asyncio
async def test_mp3_duration_seconds(tmp_path: pathlib.Path) -> None:
    filepath = os.path.join(tmp_path, 'test.mp3')
    proc = _mock_ffprobe_process(
        returncode=0,
        stdout=b'{"format": {"duration": "12.5"}}',
    )

    with mock.patch(
        'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
        mock.AsyncMock(return_value=proc),
    ):
        duration = await mp3_duration_seconds(filepath)

    assert duration == 12.5


@pytest.mark.asyncio
async def test_mp3_duration_seconds_ffprobe_error(
    tmp_path: pathlib.Path,
) -> None:
    filepath = os.path.join(tmp_path, 'test.mp3')
    proc = _mock_ffprobe_process(
        returncode=1,
        stdout=b'',
        stderr=b'invalid data',
    )

    with mock.patch(
        'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
        mock.AsyncMock(return_value=proc),
    ):
        with pytest.raises(RuntimeError, match='ffmpeg failed'):
            await mp3_duration_seconds(filepath)


@pytest.mark.asyncio
async def test_mp3_duration_seconds_no_pipes(tmp_path: pathlib.Path) -> None:
    # ffprobe fails and the subprocess has no stdout/stderr pipes attached.
    filepath = os.path.join(tmp_path, 'test.mp3')
    proc = mock.MagicMock()
    proc.returncode = 1
    proc.wait = mock.AsyncMock()
    proc.stdout = None
    proc.stderr = None

    with mock.patch(
        'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
        mock.AsyncMock(return_value=proc),
    ):
        with pytest.raises(RuntimeError, match='ffmpeg failed'):
            await mp3_duration_seconds(filepath)


@pytest.mark.asyncio
async def test_extract_audio(tmp_path: pathlib.Path) -> None:
    source = os.path.join(tmp_path, 'clip.mp4')
    mp3_path = os.path.join(tmp_path, 'out.mp3')
    proc = _mock_ffprobe_process(returncode=0, stdout=b'')

    with mock.patch(
        'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
        mock.AsyncMock(return_value=proc),
    ):
        # Should not raise
        await extract_audio(source, mp3_path)


@pytest.mark.asyncio
async def test_extract_audio_error(tmp_path: pathlib.Path) -> None:
    source = os.path.join(tmp_path, 'clip.mp4')
    mp3_path = os.path.join(tmp_path, 'out.mp3')
    proc = _mock_ffprobe_process(
        returncode=1,
        stdout=b'',
        stderr=b'Output file does not contain any stream',
    )

    with mock.patch(
        'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
        mock.AsyncMock(return_value=proc),
    ):
        with pytest.raises(ValueError, match='Could not extract audio'):
            await extract_audio(source, mp3_path)


def test_supported_video_extensions_str() -> None:
    result = supported_video_extensions_str()
    assert 'mp4' in result
    assert 'mov' in result
    # No leading dots in the human-readable string.
    assert '.' not in result


def test_member_sounds_table(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'member-sounds.db')

    member_sounds = MemberSoundTable(db_path)
    sound = MemberSound(member_id=1, guild_id=2, name='test', updated_time=0)

    member_sounds.update(sound)
    assert len(member_sounds.all(sound.guild_id)) == 1
    assert len(member_sounds.all(guild_id=42)) == 0

    assert (
        member_sounds.get(member_id=sound.member_id, guild_id=sound.guild_id)
        == sound
    )
    assert member_sounds.get(member_id=0, guild_id=0) is None

    member_sounds.remove(member_id=sound.member_id, guild_id=sound.guild_id)
    assert len(member_sounds.all(sound.guild_id)) == 0
