from __future__ import annotations

import enum
from typing import NamedTuple

from threepseat.table import SQLTableInterface


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


class RemindersTable(SQLTableInterface[Reminder]):
    """Reminders table interface."""

    def __init__(self, db_path: str) -> None:
        """Init Reminders.

        Args:
            db_path (str): path to sqlite database.
        """
        super().__init__(
            Reminder,
            'reminders',
            db_path,
            primary_keys=('guild_id', 'name'),
        )

    def _all(self, guild_id: int) -> list[Reminder]:  # type: ignore
        """Get all reminders in guild."""
        return super()._all(guild_id=guild_id)

    def _get(  # type: ignore
        self,
        guild_id: int,
        name: str,
    ) -> Reminder | None:
        """Get specific reminder."""
        return super()._get(guild_id=guild_id, name=name)

    def remove(self, guild_id: int, name: str) -> int:  # type: ignore
        """Remove a reminder."""
        return super().remove(guild_id=guild_id, name=name)
