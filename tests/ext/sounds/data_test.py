from __future__ import annotations

import pathlib
import time
from unittest import mock

import pytest

from threepseat.ext.sounds.data import MAX_SOUND_NAME_CHARS
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
    db_path = str(tmp_path / 'sounds.db')
    data_path = str(tmp_path / 'data')

    sounds = SoundsTable(db_path=db_path, data_path=data_path)
    test_sound_path = pathlib.Path(sounds.filepath(TEST_SOUND.filename))
    test_sound_path.touch()

    return sounds


def test_filepath(tmp_path: pathlib.Path) -> None:
    db_path = str(tmp_path / 'sounds.db')
    data_path = str(tmp_path / 'data')
    filename = 'testfile.mp3'

    sounds = SoundsTable(db_path=db_path, data_path=data_path)
    assert not pathlib.Path(data_path).is_dir()
    assert sounds.filepath(filename) == str(pathlib.Path(data_path) / filename)
    assert pathlib.Path(data_path).is_dir()


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


@pytest.mark.parametrize(
    ('name', 'match'),
    [
        ('../../evil', 'alphanumeric'),
        ('my sound', 'alphanumeric'),
        ('', 'between'),
        ('x' * (MAX_SOUND_NAME_CHARS + 1), 'between'),
    ],
)
def test_new_sound_validates_name(name: str, match: str) -> None:
    # The name ends up in the filename, so Sound.new must reject bad names
    # before any caller can use the path.
    with pytest.raises(ValueError, match=match):
        Sound.new(
            name=name,
            description='test sound',
            link=None,
            author_id=1234,
            guild_id=5678,
        )


def test_add_sound_exists(sounds: SoundsTable) -> None:
    sounds.add(TEST_SOUND)

    with pytest.raises(ValueError, match='exists'):
        sounds.add(TEST_SOUND)


def test_all_sounds(sounds: SoundsTable) -> None:
    sounds_list = [
        {
            'name': 'mysound1',
            'description': 'test sound1',
            'link': 'https://youtube.com/abcd1',
            'author_id': 1234,
            'guild_id': 5678,
        },
        {
            'name': 'mysound2',
            'description': 'test sound2',
            'link': 'https://youtube.com/abcd2',
            'author_id': 1234,
            'guild_id': 5678,
        },
        {
            'name': 'mysound3',
            'description': 'test sound3',
            'link': 'https://youtube.com/abcd3',
            'author_id': 1234,
            'guild_id': 0,
        },
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
    assert pathlib.Path(sounds.filepath(found1.filename)).exists()

    sounds.remove(name=TEST_SOUND.name, guild_id=TEST_SOUND.guild_id)
    found2 = sounds.get(name=TEST_SOUND.name, guild_id=TEST_SOUND.guild_id)
    assert found2 is None
    assert not pathlib.Path(sounds.filepath(found1.filename)).exists()

    # Should not error if sound does not exist
    sounds.remove(name='notasound', guild_id=123456789)


def test_youtube_download(tmp_path: pathlib.Path) -> None:
    filepath = str(tmp_path / 'test_video.mp3')
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
    filepath = str(tmp_path / 'test_video.mp3')
    link = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    with mock.patch(
        'threepseat.ext.sounds.data.YoutubeDL.extract_info',
    ) as mock_extract:
        mock_extract.return_value = {'duration': 10000}
        with pytest.raises(ValueError, match='Clip is longer than'):
            download(link, filepath)

        mock_extract.return_value = {'duration': 0}
        with (
            mock.patch(
                'threepseat.ext.sounds.data.YoutubeDL.extract_info',
                side_effect=Exception('test'),
            ),
            pytest.raises(ValueError, match='extracting'),
        ):
            download(link, filepath)

        link = 'https://www.youtube.com/watch?v=jhFDyDgMVUI'
        with (
            mock.patch(
                'threepseat.ext.sounds.data.YoutubeDL.download',
                side_effect=Exception('test'),
            ),
            pytest.raises(
                ValueError,
                match='downloading',
            ),
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
    proc.communicate = mock.AsyncMock(return_value=(stdout, stderr))
    # Real AsyncMock (not an auto-created child) so assert_not_awaited() in
    # test_mp3_duration_seconds_drains_pipes actually checks something.
    proc.wait = mock.AsyncMock()
    return proc


@pytest.mark.asyncio
async def test_mp3_duration_seconds(tmp_path: pathlib.Path) -> None:
    filepath = str(tmp_path / 'test.mp3')
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
    filepath = str(tmp_path / 'test.mp3')
    proc = _mock_ffprobe_process(
        returncode=1,
        stdout=b'',
        stderr=b'invalid data',
    )

    with (
        mock.patch(
            'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
            mock.AsyncMock(return_value=proc),
        ),
        pytest.raises(RuntimeError, match='ffprobe failed'),
    ):
        await mp3_duration_seconds(filepath)


@pytest.mark.asyncio
async def test_mp3_duration_seconds_ffprobe_error_no_output(
    tmp_path: pathlib.Path,
) -> None:
    # ffprobe failed without writing anything to stderr.
    filepath = str(tmp_path / 'test.mp3')
    proc = _mock_ffprobe_process(returncode=1, stdout=b'', stderr=b'')

    with (
        mock.patch(
            'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
            mock.AsyncMock(return_value=proc),
        ),
        pytest.raises(RuntimeError, match='ffprobe failed'),
    ):
        await mp3_duration_seconds(filepath)


@pytest.mark.asyncio
async def test_mp3_duration_seconds_drains_pipes(
    tmp_path: pathlib.Path,
) -> None:
    # The pipes must be drained while waiting; reading them only after wait()
    # deadlocks when the child fills the OS pipe buffer.
    filepath = str(tmp_path / 'test.mp3')
    proc = _mock_ffprobe_process(
        returncode=0,
        stdout=b'{"format": {"duration": "1.0"}}',
    )

    with mock.patch(
        'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
        mock.AsyncMock(return_value=proc),
    ):
        await mp3_duration_seconds(filepath)

    proc.communicate.assert_awaited_once()
    proc.wait.assert_not_awaited()


@pytest.mark.asyncio
async def test_extract_audio(tmp_path: pathlib.Path) -> None:
    source = str(tmp_path / 'clip.mp4')
    mp3_path = str(tmp_path / 'out.mp3')
    proc = _mock_ffprobe_process(returncode=0, stdout=b'')

    with mock.patch(
        'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
        mock.AsyncMock(return_value=proc),
    ):
        # Should not raise
        await extract_audio(source, mp3_path)


@pytest.mark.asyncio
async def test_extract_audio_error(tmp_path: pathlib.Path) -> None:
    source = str(tmp_path / 'clip.mp4')
    mp3_path = str(tmp_path / 'out.mp3')
    proc = _mock_ffprobe_process(
        returncode=1,
        stdout=b'',
        stderr=b'Output file does not contain any stream',
    )

    with (
        mock.patch(
            'threepseat.ext.sounds.data.asyncio.create_subprocess_exec',
            mock.AsyncMock(return_value=proc),
        ),
        pytest.raises(ValueError, match='Could not extract audio'),
    ):
        await extract_audio(source, mp3_path)


def test_supported_video_extensions_str() -> None:
    result = supported_video_extensions_str()
    assert 'mp4' in result
    assert 'mov' in result
    # No leading dots in the human-readable string.
    assert '.' not in result


def test_member_sounds_table(tmp_path: pathlib.Path) -> None:
    db_path = str(tmp_path / 'member-sounds.db')

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
