from __future__ import annotations

from typing import NamedTuple

from threepseat.table import SQLTableInterface


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


class BirthdayTable(SQLTableInterface[Birthday]):
    """Birthday table interface."""

    def __init__(self, db_path: str) -> None:
        """Init BirthdayTable.

        Args:
            db_path (str): path to sqlite database.
        """
        super().__init__(
            Birthday,
            'birthdays',
            db_path,
            primary_keys=('guild_id', 'user_id'),
        )

    def _all(self, guild_id: int) -> list[Birthday]:  # type: ignore
        """Get all birthdays in guild."""
        return super()._all(guild_id=guild_id)

    def _get(  # type: ignore
        self,
        guild_id: int,
        user_id: int,
    ) -> Birthday | None:
        """Get users birthday."""
        return super()._get(guild_id=guild_id, user_id=user_id)

    def remove(self, guild_id: int, user_id: int) -> int:  # type: ignore
        """Remove a birthday from the table."""
        return super().remove(guild_id=guild_id, user_id=user_id)
