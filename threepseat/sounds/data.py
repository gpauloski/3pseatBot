from __future__ import annotations

import contextlib
import sqlite3
import time
import uuid
from typing import Generator
from typing import NamedTuple

from threepseat.database import create_table
from threepseat.utils import alphanumeric


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

        self.download(sound.link, sound.filename)

        with self.connect() as db:
            db.execute(
                'INSERT INTO sounds VALUES '
                '(:uuid, :name, :description, :link, :author_id, :guild_id, '
                ':created_time, :filename)',
                sound._asdict(),
            )

    def download(self, link: str, filename: str) -> None:
        """Download sound from YouTube."""
        ...

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
        with self.connect() as db:
            db.execute(
                'DELETE FROM sounds '
                'WHERE name = :name AND guild_id = :guild_id',
                {'guild_id': guild_id, 'name': name},
            )
