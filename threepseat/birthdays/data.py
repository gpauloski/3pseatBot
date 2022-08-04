from __future__ import annotations

import contextlib
import functools
import os
import sqlite3
from collections.abc import Generator
from typing import NamedTuple

from threepseat.database import create_table
from threepseat.database import named_tuple_parameters
from threepseat.database import named_tuple_parameters_update


class UnknownBirthdayError(Exception):
    """Exception raised when removing a birthday that does not exist."""

    pass


class Birthday(NamedTuple):
    """Row in birthday table.

    guild_id and user_id server as compound primary key.
    """

    guild_id: int
    """Guild this birthday was add in."""
    user_id: int
    """User this birthday is for."""
    author_id: int
    """User that added the birthday."""
    creation_time: int
    """Unix timestamp of when the birthday was added."""
    birth_day: int
    """Day of month of birthday."""
    birth_month: int
    """Number of month of birthday."""


class Birthdays:
    """Birthday data manager."""

    def __init__(self, db_path: str) -> None:
        """Init Birthdays.

        Args:
            db_path (str): path to sqlite database.
        """
        self.db_path = db_path

        if len(os.path.dirname(self.db_path)) > 0:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.all = functools.cache(self._all)
        self.get = functools.cache(self._get)

        with self.connect() as db:
            create_table(db, 'birthdays', Birthday)

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Database connection context manager."""
        with contextlib.closing(sqlite3.connect(self.db_path)) as db:
            with db:
                yield db

    def _all(self, guild_id: int) -> list[Birthday]:
        """Get all birthdays in guild."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM birthdays WHERE guild_id = :guild_id',
                {'guild_id': guild_id},
            ).fetchall()
            return [Birthday(*row) for row in rows]

    def _get(self, guild_id: int, user_id: int) -> Birthday | None:
        """Get users birthday."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM birthdays '
                'WHERE guild_id = :guild_id AND user_id = :user_id',
                {'guild_id': guild_id, 'user_id': user_id},
            ).fetchall()
            if len(rows) == 0:
                return None
            else:
                return Birthday(*rows[0])

    def update(self, birthday: Birthday) -> None:
        """Add or update a birthday."""
        with self.connect() as db:
            res = db.execute(
                'UPDATE birthdays '
                f'SET {named_tuple_parameters_update(Birthday)} '
                'WHERE guild_id = :guild_id AND user_id = :user_id',
                birthday._asdict(),
            )
            if res.rowcount == 0:
                res = db.execute(
                    'INSERT INTO birthdays VALUES '
                    f'{named_tuple_parameters(Birthday)}',
                    birthday._asdict(),
                )
            self.get.cache_clear()
            self.all.cache_clear()

    def remove(self, guild_id: int, user_id: int) -> None:
        """Remove a birthday."""
        birthday = self.get(guild_id, user_id)
        if birthday is None:
            raise UnknownBirthdayError()

        with self.connect() as db:
            db.execute(
                'DELETE FROM birthdays '
                'WHERE guild_id = :guild_id AND user_id = :user_id',
                {'guild_id': guild_id, 'user_id': user_id},
            )

        self.get.cache_clear()
        self.all.cache_clear()
