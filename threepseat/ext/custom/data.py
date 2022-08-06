from __future__ import annotations

from typing import NamedTuple

from threepseat.table import SQLTableInterface


class CustomCommand(NamedTuple):
    """Row for custom command in database."""

    name: str
    description: str
    body: str
    author_id: int
    guild_id: int
    creation_time: float


class CustomCommandTable(SQLTableInterface[CustomCommand]):
    """Custom command table interface."""

    def __init__(self, db_path: str) -> None:
        """Init CustomCommandTable.

        Args:
            db_path (str): path to sqlite database.
        """
        super().__init__(
            CustomCommand,
            'custom_commands',
            db_path,
            primary_keys=('guild_id', 'name'),
        )

    def _all(  # type: ignore
        self,
        guild_id: int | None = None,
    ) -> list[CustomCommand]:
        """Get all custom commands in guild."""
        if guild_id is None:
            return super()._all()
        return super()._all(guild_id=guild_id)

    def _get(  # type: ignore
        self,
        guild_id: int,
        name: str,
    ) -> CustomCommand | None:
        """Get custom command in guild."""
        return super()._get(guild_id=guild_id, name=name)

    def remove(self, guild_id: int, name: str) -> int:  # type: ignore
        """Remove a custom command from the table."""
        return super().remove(guild_id=guild_id, name=name)
