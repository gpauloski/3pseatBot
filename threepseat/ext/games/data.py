from __future__ import annotations

from typing import NamedTuple

from threepseat.table import SQLTableInterface


class Game(NamedTuple):
    """Row in games table.

    guild_id and name serve as the compound primary key.
    """

    guild_id: int
    """Guild this game was added in."""
    author_id: int
    """User that added the game."""
    creation_time: int
    """Unix timestamp of when the game was added."""
    name: str
    """Name of the game."""


class GamesTable(SQLTableInterface[Game]):
    """Games table interface."""

    def __init__(self, db_path: str) -> None:
        """Init GamesTable.

        Args:
            db_path (str): path to sqlite database.
        """
        super().__init__(
            Game,
            'games',
            db_path,
            primary_keys=('guild_id', 'name'),
        )

    def _all(self, guild_id: int) -> list[Game]:  # type: ignore
        """Get all games in guild."""
        return super()._all(guild_id=guild_id)

    def _get(self, guild_id: int, name: str) -> Game | None:  # type: ignore
        """Get game in table."""
        return super()._get(guild_id=guild_id, name=name)

    def remove(self, guild_id: int, name: str) -> int:  # type: ignore
        """Remove a game from the table."""
        return super().remove(guild_id=guild_id, name=name)
