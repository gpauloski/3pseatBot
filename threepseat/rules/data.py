from __future__ import annotations

import contextlib
import functools
import os
import sqlite3
import time
from typing import Generator
from typing import NamedTuple

from threepseat.database import create_table
from threepseat.database import named_tuple_parameters
from threepseat.database import named_tuple_parameters_update
from threepseat.rules.exceptions import GuildNotConfiguredError
from threepseat.rules.exceptions import MaxOffensesExceededError


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

    def add_offense(self, guild_id: int, user_id: int) -> int:
        """Add offense to user in guild."""
        config = self.get_config(guild_id)
        if config is None:
            raise GuildNotConfiguredError()
        user = self.get_user(guild_id, user_id)
        if user is None:
            user = UserOffenses(
                guild_id=guild_id,
                user_id=user_id,
                current_offenses=1,
                total_offenses=1,
                last_offense=time.time(),
            )
        else:
            user = user._replace(
                current_offenses=user.current_offenses + 1,
                total_offenses=user.total_offenses + 1,
            )
        self.update_user(user)
        if user.current_offenses >= config.max_offenses:
            raise MaxOffensesExceededError()
        return user.current_offenses

    def remove_offense(self, guild_id: int, user_id: int) -> None:
        """Remove offense from user in guild."""
        user = self.get_user(guild_id, user_id)
        if user is not None:
            user = user._replace(
                current_offenses=max(0, user.current_offenses - 1),
                total_offenses=max(0, user.total_offenses - 1),
            )
            self.update_user(user)

    def reset_current_offenses(self, guild_id: int, user_id: int) -> None:
        """Reset current offenses for user in guild."""
        user = self.get_user(guild_id, user_id)
        if user is not None:
            user = user._replace(current_offenses=0)
            self.update_user(user)
