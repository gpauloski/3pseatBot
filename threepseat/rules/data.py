from __future__ import annotations

import contextlib
import functools
import os
import sqlite3
from typing import Generator
from typing import NamedTuple

from threepseat.database import create_table
from threepseat.database import named_tuple_parameters
from threepseat.database import named_tuple_parameters_update


class ChannelConfig(NamedTuple):
    """Row in channel config database table."""

    guild_id: int
    channel_id: int
    event_expectancy: float
    event_duration: float
    event_cooldown: float
    last_event: int
    max_offenses: int
    timeout_duration: int
    prefixes: str


class UserOffenses(NamedTuple):
    """Row in user offenses database table."""

    guild_id: int
    channel_id: int
    user_id: int
    current_offenses: int
    total_offenses: int
    last_offense: int


class Rules:
    """Rules data manager."""

    def __init__(self, db_path: str) -> None:
        """Init Rules.

        Args:
            db_path (str): path to sqlite database.
        """
        self.db_path = db_path

        if len(os.path.dirname(self.db_path)) > 0:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.get_config_cached = functools.lru_cache(maxsize=None)(
            self.get_config,
        )
        self.get_user_cached = functools.lru_cache(maxsize=None)(self.get_user)
        self.get_users_cached = functools.lru_cache(maxsize=None)(
            self.get_users,
        )

        with self.connect() as db:
            create_table(db, 'channel_configs', ChannelConfig)
            create_table(db, 'user_offenses', UserOffenses)

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Database connection context manager."""
        with contextlib.closing(sqlite3.connect(self.db_path)) as db:
            with db:
                yield db

    def get_config(
        self,
        guild_id: int,
        channel_id: int,
    ) -> ChannelConfig | None:
        """Get channel config matching guild and channel id."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM channel_configs '
                'WHERE guild_id = :guild_id AND channel_id = :channel_id',
                {'guild_id': guild_id, 'channel_id': channel_id},
            ).fetchall()
            if len(rows) == 0:
                return None
            else:
                return ChannelConfig(*rows[0])

    def update_config(self, config: ChannelConfig) -> None:
        """Update channel config row that matches the guild and channel id."""
        with self.connect() as db:
            res = db.execute(
                'UPDATE channel_configs '
                f'SET {named_tuple_parameters_update(ChannelConfig)} '
                'WHERE guild_id = :guild_id AND channel_id = :channel_id',
                config._asdict(),
            )
            if res.rowcount == 0:
                res = db.execute(
                    'INSERT INTO channel_configs VALUES '
                    f'{named_tuple_parameters(ChannelConfig)}',
                    config._asdict(),
                )
            if res.rowcount > 0:
                self.get_config_cached.cache_clear()

    def get_user(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
    ) -> UserOffenses | None:
        """Get the user offenses matching the guild, channel, and user id."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM user_offenses '
                'WHERE guild_id = :guild_id AND channel_id = :channel_id '
                'AND user_id = :user_id',
                {
                    'guild_id': guild_id,
                    'channel_id': channel_id,
                    'user_id': user_id,
                },
            ).fetchall()
            if len(rows) == 0:
                return None
            else:
                return UserOffenses(*rows[0])

    def get_users(self, guild_id: int, channel_id: int) -> list[UserOffenses]:
        """Get all user offenses matching a guild and channel id."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM user_offenses '
                'WHERE guild_id = :guild_id AND channel_id = :channel_id',
                {'guild_id': guild_id, 'channel_id': channel_id},
            ).fetchall()
            return [UserOffenses(*row) for row in rows]

    def update_user(self, user: UserOffenses) -> None:
        """Update user offenses row matching the guild, channel, user id."""
        with self.connect() as db:
            res = db.execute(
                'UPDATE user_offenses '
                f'SET {named_tuple_parameters_update(UserOffenses)} '
                'WHERE guild_id = :guild_id AND channel_id = :channel_id '
                'AND user_id = :user_id',
                user._asdict(),
            )
            if res.rowcount == 0:
                res = db.execute(
                    'INSERT INTO user_offenses VALUES '
                    f'{named_tuple_parameters(UserOffenses)}',
                    user._asdict(),
                )
            if res.rowcount > 0:
                self.get_user_cached.cache_clear()
                self.get_users_cached.cache_clear()
