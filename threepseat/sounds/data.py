from __future__ import annotations

import contextlib
import sqlite3
from typing import Generator
from typing import NamedTuple


class Sound(NamedTuple):
    """Representation of entry in sounds database."""

    uuid: str
    name: str
    description: str
    link: str | None
    author_id: int
    guild_id: int
    created_time: int
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
        """Add sound to database."""
        ...

    def download(self, link: str, filepath: str) -> None:
        """Download sound from YouTube."""
        ...

    def get(self, name: str, guild_id: str) -> Sound | None:
        """Get sound in database."""
        ...

    def list(self, guild_id: str) -> list[Sound]:
        """List sounds in database."""
        ...

    def remove(self, name: str, guild_id: str) -> Sound:
        """Remove sound from database."""
        ...
