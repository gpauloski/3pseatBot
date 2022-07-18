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


class GuildConfig(NamedTuple):
    """Row in Guild config database table."""

    guild_id: int
    """Guild this config is for."""
    enabled: int
    """Events enabled flag."""
    event_expectancy: float
    """Expected number of events per day."""
    event_duration: float
    """Event duration in minutes."""
    event_cooldown: float
    """Event cooldown in minutes (not used)."""
    last_event: float
    """Unix timestamp of last event occurrence (0 for no occurrences)."""
    max_offenses: int
    """Max offenses a member can get."""
    timeout_duration: float
    """Timeout in minutes when a user exceeds max_offenses."""
    prefixes: str
    """Comma separated list of allowed prefixes (case-insensitive)."""


class UserOffenses(NamedTuple):
    """Row in user offenses database table."""

    guild_id: int
    """Guild the user got the offenses in."""
    user_id: int
    """User id with the offenses."""
    current_offenses: int
    """Current number of offenses in the guild."""
    total_offenses: int
    """Lifetime number of offenses in the guild."""
    last_offense: float
    """Unix timestamp of last offense in the guild."""


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

        self.get_config = functools.lru_cache(maxsize=None)(self._get_config)
        self.get_configs = functools.lru_cache(maxsize=None)(self._get_configs)
        self.get_user = functools.lru_cache(maxsize=None)(self._get_user)
        self.get_users = functools.lru_cache(maxsize=None)(self._get_users)

        with self.connect() as db:
            create_table(db, 'guild_configs', GuildConfig)
            create_table(db, 'user_offenses', UserOffenses)

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Database connection context manager."""
        with contextlib.closing(sqlite3.connect(self.db_path)) as db:
            with db:
                yield db

    def _get_config(self, guild_id: int) -> GuildConfig | None:
        """Get configuration for guild."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM guild_configs WHERE guild_id = :guild_id',
                {'guild_id': guild_id},
            ).fetchall()
            if len(rows) == 0:
                return None
            else:
                return GuildConfig(*rows[0])

    def _get_configs(self) -> list[GuildConfig]:
        """Get all guild configs."""
        with self.connect() as db:
            rows = db.execute('SELECT * FROM guild_configs').fetchall()
            return [GuildConfig(*row) for row in rows]

    def update_config(self, config: GuildConfig) -> None:
        """Update config row matching guild id."""
        with self.connect() as db:
            res = db.execute(
                'UPDATE guild_configs '
                f'SET {named_tuple_parameters_update(GuildConfig)} '
                'WHERE guild_id = :guild_id',
                config._asdict(),
            )
            if res.rowcount == 0:
                res = db.execute(
                    'INSERT INTO guild_configs VALUES '
                    f'{named_tuple_parameters(GuildConfig)}',
                    config._asdict(),
                )
            self.get_config.cache_clear()
            self.get_configs.cache_clear()

    def _get_user(
        self,
        guild_id: int,
        user_id: int,
    ) -> UserOffenses | None:
        """Get the user offenses matching the guild and user id."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM user_offenses '
                'WHERE guild_id = :guild_id AND user_id = :user_id',
                {'guild_id': guild_id, 'user_id': user_id},
            ).fetchall()
            if len(rows) == 0:
                return None
            else:
                return UserOffenses(*rows[0])

    def _get_users(self, guild_id: int) -> list[UserOffenses]:
        """Get all user offenses in a guild."""
        with self.connect() as db:
            rows = db.execute(
                'SELECT * FROM user_offenses WHERE guild_id = :guild_id',
                {'guild_id': guild_id},
            ).fetchall()
            return [UserOffenses(*row) for row in rows]

    def update_user(self, user: UserOffenses) -> None:
        """Update user offenses row matching the guild and user id."""
        with self.connect() as db:
            res = db.execute(
                'UPDATE user_offenses '
                f'SET {named_tuple_parameters_update(UserOffenses)} '
                'WHERE guild_id = :guild_id AND user_id = :user_id',
                user._asdict(),
            )
            if res.rowcount == 0:
                res = db.execute(
                    'INSERT INTO user_offenses VALUES '
                    f'{named_tuple_parameters(UserOffenses)}',
                    user._asdict(),
                )
            self.get_user.cache_clear()
            self.get_users.cache_clear()
