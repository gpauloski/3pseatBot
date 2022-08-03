from __future__ import annotations

import contextlib
import enum
import functools
import os
import sqlite3
from collections.abc import Generator
from typing import NamedTuple

from threepseat.database import create_table
from threepseat.database import named_tuple_parameters
from threepseat.database import named_tuple_parameters_update


class UnknownReminderError(Exception):
    """Exception raised when modifying a reminder that does not exist."""

    pass


class ReminderType(enum.Enum):
    """Reminder Type."""

    ONE_TIME = 'one-time'
    REPEATING = 'repeating'


class Reminder(NamedTuple):
    """Row in reminder table.

    guild_id and name serve as a compound primary key.
    """

    guild_id: int
    """Guild this reminder is configured in."""
    channel_id: int
    """Channel ID to send reminedr in."""
    author_id: int
    """User who created the reminder."""
    creation_time: int
    """Unix timestamp of when reminder was created."""
    name: str
    """Name of the reminder. Used for administrative purposes."""
    text: str
    """Reminder message."""
    delay_minutes: int
    """Minutes between saying reminder message."""


class Reminders:
    """Reminders data manager."""

    def __init__(self, db_path: str) -> None:
        """Init Reminders.

        Args:
            db_path (str): path to sqlite database.
        """
        self.db_path = db_path

        if len(os.path.dirname(self.db_path)) > 0:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.all = functools.cache(self._all)
        self.get = functools.cache(self._get)

        with self.connect() as db:
            create_table(db, 'reminders', Reminder)

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Database connection context manager."""
        with contextlib.closing(sqlite3.connect(self.db_path)) as db:
            with db:
                yield db

    def _all(self, guild_id: int) -> list[Reminder]:
        """Get all reminders in guild."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM reminders WHERE guild_id = :guild_id',
                {'guild_id': guild_id},
            ).fetchall()
            return [Reminder(*row) for row in rows]

    def _get(self, guild_id: int, name: str) -> Reminder | None:
        """Get specific reminder."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM reminders '
                'WHERE guild_id = :guild_id AND name = :name',
                {'guild_id': guild_id, 'name': name},
            ).fetchall()
            if len(rows) == 0:
                return None
            else:
                return Reminder(*rows[0])

    def update(self, reminder: Reminder) -> None:
        """Add or update a reminder."""
        with self.connect() as db:
            res = db.execute(
                'UPDATE reminders '
                f'SET {named_tuple_parameters_update(Reminder)} '
                'WHERE guild_id = :guild_id AND name = :name',
                reminder._asdict(),
            )
            if res.rowcount == 0:
                res = db.execute(
                    'INSERT INTO reminders VALUES '
                    f'{named_tuple_parameters(Reminder)}',
                    reminder._asdict(),
                )
            self.get.cache_clear()
            self.all.cache_clear()

    def remove(self, guild_id: int, name: str) -> None:
        """Remove a reminder."""
        reminder = self.get(guild_id, name)
        if reminder is None:
            raise UnknownReminderError()

        with self.connect() as db:
            db.execute(
                'DELETE FROM reminders '
                'WHERE name = :name AND guild_id = :guild_id',
                {'guild_id': guild_id, 'name': name},
            )

        self.get.cache_clear()
        self.all.cache_clear()
