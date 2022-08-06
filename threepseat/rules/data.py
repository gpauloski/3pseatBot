from __future__ import annotations

import time
from typing import NamedTuple

from threepseat.rules.exceptions import GuildNotConfiguredError
from threepseat.rules.exceptions import MaxOffensesExceededError
from threepseat.table import SQLTableInterface


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


class RulesDatabase:
    """Rules database interface."""

    def __init__(self, db_path: str) -> None:
        """Init RulesDatabase.

        Args:
            db_path (str): path to sqlite database.
        """
        self.config_table = GuildConfigTable(db_path)
        self.offenses_table = UserOffensesTable(db_path)

    def get_config(self, guild_id: int) -> GuildConfig | None:
        """Get configuration for guild."""
        return self.config_table.get(guild_id)

    def get_configs(self) -> list[GuildConfig]:
        """Get all guild configs."""
        return self.config_table.all()

    def update_config(self, config: GuildConfig) -> None:
        """Update config row matching guild id."""
        return self.config_table.update(config)

    def get_user(
        self,
        guild_id: int,
        user_id: int,
    ) -> UserOffenses | None:
        """Get the user offenses matching the guild and user id."""
        return self.offenses_table.get(guild_id, user_id)

    def get_users(self, guild_id: int) -> list[UserOffenses]:
        """Get all user offenses in a guild."""
        return self.offenses_table.all(guild_id)

    def update_user(self, user: UserOffenses) -> None:
        """Update user offenses row matching the guild and user id."""
        return self.offenses_table.update(user)

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


class GuildConfigTable(SQLTableInterface[GuildConfig]):
    """Guild config table interface."""

    def __init__(self, db_path: str) -> None:
        """Init GuildConfigTable.

        Args:
            db_path (str): path to sqlite database.
        """
        super().__init__(
            GuildConfig,
            'guild_configs',
            db_path,
            primary_keys=('guild_id',),
        )

    def _all(self) -> list[GuildConfig]:  # type: ignore
        """Get guild configs."""
        return super()._all()

    def _get(self, guild_id: int) -> GuildConfig | None:  # type: ignore
        """Get guild config."""
        return super()._get(guild_id=guild_id)

    def remove(self, guild_id: int) -> int:  # type: ignore
        """Remove a guild config from the table."""
        raise NotImplementedError


class UserOffensesTable(SQLTableInterface[UserOffenses]):
    """User offenses table interface."""

    def __init__(self, db_path: str) -> None:
        """Init GuildConfigTable.

        Args:
            db_path (str): path to sqlite database.
        """
        super().__init__(
            UserOffenses,
            'user_offenses',
            db_path,
            primary_keys=('guild_id', 'user_id'),
        )

    def _all(self, guild_id: int) -> list[UserOffenses]:  # type: ignore
        """Get all user offenses in the guild."""
        return super()._all(guild_id=guild_id)

    def _get(  # type: ignore
        self,
        guild_id: int,
        user_id: int,
    ) -> UserOffenses | None:
        """Get user offenses."""
        return super()._get(guild_id=guild_id, user_id=user_id)

    def remove(self, guild_id: int, user_id: int) -> int:  # type: ignore
        """Remove a row."""
        raise NotImplementedError
