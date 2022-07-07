from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import time
import uuid
from typing import Generator
from typing import NamedTuple

import youtube_dl

from threepseat.database import create_table
from threepseat.utils import alphanumeric


MAX_SOUND_LENGTH_SECONDS = 30

logger = logging.getLogger(__name__)


class Sound(NamedTuple):
    """Representation of entry in sounds database."""

    uuid: str
    name: str
    description: str
    link: str
    author_id: int
    guild_id: int
    created_time: float
    filename: str


class Sounds:
    """Sounds data manager."""

    def __init__(self, db_path: str, data_path: str) -> None:
        """Init Sounds.

        Args:
            db_path (str): path to sqlite database.
            data_path (str): directory where sound files are stored.
        """
        self.db_path = db_path
        self.data_path = data_path
        self.values = (
            '(uuid TEXT, name TEXT, description TEXT, link TEXT, '
            'author_id INTEGER, guild_id INTEGER, created_time REAL, '
            'filename TEXT)'
        )

        with self.connect() as db:
            create_table(db, 'sounds', self.values)

    def filepath(self, filename: str) -> str:
        """Get filepath for filename."""
        os.makedirs(self.data_path, exist_ok=True)
        return os.path.join(self.data_path, filename)

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Database connection context manager."""
        # Source: https://github.com/pre-commit/pre-commit/blob/354b900f15e88a06ce8493e0316c288c44777017/pre_commit/store.py#L91  # noqa: E501
        with contextlib.closing(sqlite3.connect(self.db_path)) as db:
            with db:
                yield db

    def add(
        self,
        name: str,
        description: str,
        link: str,
        author_id: int,
        guild_id: int,
    ) -> None:
        """Add sound to database.

        Raises:
            ValueError:
                if name contains non-alphanumeric characters.
            ValueError:
                if name is not between 1 and 12 characters long.
            ValueError:
                any additional errors raises by download().
        """
        if not alphanumeric(name):
            raise ValueError('Name must contain only alphanumeric characters.')
        if len(name) == 0 or len(name) > 12:
            raise ValueError('Name must be between 1 and 12 characters long.')

        existing = self.get(name=name, guild_id=guild_id)
        if existing is not None:
            raise ValueError('Sound with that name already exists.')

        uuid_ = uuid.uuid4()
        sound = Sound(
            uuid=str(uuid_),
            name=name,
            description=description,
            link=link,
            author_id=author_id,
            guild_id=guild_id,
            created_time=time.time(),
            filename=f'{uuid_}-{name}-{guild_id}.mp3',
        )

        download(sound.link, self.filepath(sound.filename))

        with self.connect() as db:
            db.execute(
                'INSERT INTO sounds VALUES '
                '(:uuid, :name, :description, :link, :author_id, :guild_id, '
                ':created_time, :filename)',
                sound._asdict(),
            )

        logger.info(f'added sound to database: {sound}')

    def get(self, name: str, guild_id: int) -> Sound | None:
        """Get sound in database."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM sounds '
                'WHERE name = :name AND guild_id = :guild',
                {'name': name, 'guild': guild_id},
            ).fetchall()
            if len(rows) == 0:
                return None
            else:
                return Sound(*rows[0])

    def list(self, guild_id: int) -> list[Sound]:
        """List sounds in database."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM sounds WHERE guild_id = :guild_id',
                {'guild_id': guild_id},
            )
            return [Sound(*row) for row in rows]

    def remove(self, name: str, guild_id: int) -> None:
        """Remove sound from database."""
        sound = self.get(name, guild_id)

        if sound is not None:
            with self.connect() as db:
                db.execute(
                    'DELETE FROM sounds '
                    'WHERE name = :name AND guild_id = :guild_id',
                    {'guild_id': guild_id, 'name': name},
                )

            filepath = self.filepath(sound.filename)
            os.remove(filepath)

            logger.info(
                'removed sound from database: '
                f'(name={name}, guild_id={guild_id})',
            )


def download(link: str, filepath: str) -> None:
    """Download sound from YouTube.

    Args:
        link (str): youtube link to download.
        filepath (str): filepath for downloaded file.

    Raises:
        ValueError:
            if the clip is longer than MAX_SOUND_LENGTH_SECONDS.
        ValueError:
            if there is an error downloading the clip.
    """
    ydl_opts = {
        'outtmpl': filepath,
        'format': 'worst',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            },
        ],
        'logger': logger,
        'socket_timeout': 30,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            metadata = ydl.extract_info(
                link,
                download=False,
                process=False,
            )
        except Exception as e:
            logger.exception(
                f'caught error extracting sound metadata: {e}',
            )
            raise ValueError('Error extracting sound metadata.')

        if int(metadata['duration']) > MAX_SOUND_LENGTH_SECONDS:
            raise ValueError(
                f'Clip is longer than {MAX_SOUND_LENGTH_SECONDS} ' 'seconds.',
            )

        try:
            ydl.download([link])
        except Exception as e:
            logger.exception(f'caught error downloading sound: {e}')
            raise ValueError('Error downloading sound.')
