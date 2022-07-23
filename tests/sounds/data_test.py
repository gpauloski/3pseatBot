from __future__ import annotations

import os
import pathlib
import time
from unittest import mock

import pytest

from threepseat.sounds.data import download
from threepseat.sounds.data import Sound
from threepseat.sounds.data import Sounds

TEST_SOUND = Sound(
    uuid='abcd-efgh',
    name='mysounds',
    description='test sound',
    link='https://youtube.com/abcd',
    author_id=1234,
    guild_id=5678,
    created_time=0,
    filename='mysound.mp3',
)


@pytest.fixture(autouse=True)
def _mock_download(mock_download) -> None:
    pass


def test_table_created(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')

    sounds = Sounds(db_path=db_path, data_path='')

    with sounds.connect() as db:
        res = db.execute(
            'SELECT COUNT(*) FROM sqlite_master '
            'WHERE type="table" AND name="sounds"',
        ).fetchone()
        assert res[0] == 1


def test_filepath(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')
    filename = 'testfile.mp3'

    sounds = Sounds(db_path=db_path, data_path=data_path)
    assert not os.path.isdir(data_path)
    assert sounds.filepath(filename) == os.path.join(data_path, filename)
    assert os.path.isdir(data_path)


def test_add_get_sound(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')

    sounds = Sounds(db_path=db_path, data_path=data_path)

    sounds.add(
        name=TEST_SOUND.name,
        description=TEST_SOUND.description,
        link=TEST_SOUND.link,
        author_id=TEST_SOUND.author_id,
        guild_id=TEST_SOUND.guild_id,
    )

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


def test_add_sound_validation(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')

    sounds = Sounds(db_path=db_path, data_path=data_path)

    with pytest.raises(ValueError, match='alphanumeric'):
        sounds.add(
            name='my sound',
            description=TEST_SOUND.description,
            link=TEST_SOUND.link,
            author_id=TEST_SOUND.author_id,
            guild_id=TEST_SOUND.guild_id,
        )

    with pytest.raises(ValueError, match='alphanumeric'):
        sounds.add(
            name='mysound%',
            description=TEST_SOUND.description,
            link=TEST_SOUND.link,
            author_id=TEST_SOUND.author_id,
            guild_id=TEST_SOUND.guild_id,
        )

    with pytest.raises(ValueError, match='between'):
        sounds.add(
            name='',
            description=TEST_SOUND.description,
            link=TEST_SOUND.link,
            author_id=TEST_SOUND.author_id,
            guild_id=TEST_SOUND.guild_id,
        )

    with pytest.raises(ValueError, match='between'):
        sounds.add(
            name='xxxxxxxxxxxxxxxx',
            description=TEST_SOUND.description,
            link=TEST_SOUND.link,
            author_id=TEST_SOUND.author_id,
            guild_id=TEST_SOUND.guild_id,
        )


def test_add_sound_exists(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')

    sounds = Sounds(db_path=db_path, data_path=data_path)

    sounds.add(
        name=TEST_SOUND.name,
        description=TEST_SOUND.description,
        link=TEST_SOUND.link,
        author_id=TEST_SOUND.author_id,
        guild_id=TEST_SOUND.guild_id,
    )

    with pytest.raises(ValueError, match='exists'):
        sounds.add(
            name=TEST_SOUND.name,
            description=TEST_SOUND.description,
            link=TEST_SOUND.link,
            author_id=TEST_SOUND.author_id,
            guild_id=TEST_SOUND.guild_id,
        )


def test_list_sounds(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')

    sounds = Sounds(db_path=db_path, data_path=data_path)

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

    for sound in sounds_list:
        sounds.add(
            name=sound['name'],  # type: ignore
            description=sound['description'],  # type: ignore
            link=sound['link'],  # type: ignore
            author_id=sound['author_id'],  # type: ignore
            guild_id=sound['guild_id'],  # type: ignore
        )

    assert len(sounds.list(guild_id=-1)) == 0
    assert len(sounds.list(guild_id=0)) == 1
    found = sounds.list(guild_id=5678)
    assert len(found) == 2

    names = {s.name for s in found}
    assert names == {'mysound1', 'mysound2'}


def test_remove_sound(tmp_path: pathlib.Path) -> None:
    db_path = os.path.join(tmp_path, 'sounds.db')
    data_path = os.path.join(tmp_path, 'data')

    sounds = Sounds(db_path=db_path, data_path=data_path)

    sounds.add(
        name=TEST_SOUND.name,
        description=TEST_SOUND.description,
        link=TEST_SOUND.link,
        author_id=TEST_SOUND.author_id,
        guild_id=TEST_SOUND.guild_id,
    )

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
            'youtube_dl.YoutubeDL.extract_info',
            return_value={'duration': 0.1},
        ),
        mock.patch('youtube_dl.YoutubeDL.download'),
    ):
        download(link, filepath)


def test_youtube_download_errors(tmp_path: pathlib.Path) -> None:
    filepath = os.path.join(tmp_path, 'test_video.mp3')
    link = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    with mock.patch('youtube_dl.YoutubeDL.extract_info') as mock_extract:
        mock_extract.return_value = {'duration': 10000}
        with pytest.raises(ValueError, match='Clip is longer than'):
            download(link, filepath)

        mock_extract.return_value = {'duration': 0}
        with mock.patch(
            'youtube_dl.YoutubeDL.extract_info',
            side_effect=Exception('test'),
        ):
            with pytest.raises(ValueError, match='extracting'):
                download(link, filepath)

        link = 'https://www.youtube.com/watch?v=jhFDyDgMVUI'
        with mock.patch(
            'youtube_dl.YoutubeDL.download',
            side_effect=Exception('test'),
        ):
            with pytest.raises(ValueError, match='downloading'):
                download(link, filepath)
