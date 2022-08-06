from __future__ import annotations

import pytest

from threepseat.rules.data import GuildConfig
from threepseat.rules.data import RulesDatabase
from threepseat.rules.data import UserOffenses
from threepseat.rules.exceptions import GuildNotConfiguredError
from threepseat.rules.exceptions import MaxOffensesExceededError

GUILD_CONFIG = GuildConfig(
    guild_id=1234,
    enabled=1,
    event_expectancy=0.5,
    event_duration=24,
    event_cooldown=5.0,
    last_event=0,
    max_offenses=3,
    timeout_duration=300,
    prefixes='3pseat, 3pfeet',
)


USER_OFFENSES = UserOffenses(
    guild_id=1234,
    user_id=9012,
    current_offenses=0,
    total_offenses=0,
    last_offense=0,
)


def test_get_configs(tmp_file: str) -> None:
    rules = RulesDatabase(db_path=tmp_file)

    assert len(rules.get_configs()) == 0

    rules.update_config(GUILD_CONFIG._replace(guild_id=1))
    rules.update_config(GUILD_CONFIG._replace(guild_id=2))
    rules.update_config(GUILD_CONFIG._replace(guild_id=3))
    rules.update_config(GUILD_CONFIG._replace(guild_id=4))

    configs = rules.get_configs()
    assert len(configs) == 4
    assert {config.guild_id for config in configs} == {1, 2, 3, 4}


def test_get_users(tmp_file: str) -> None:
    rules = RulesDatabase(db_path=tmp_file)

    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=1))
    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=2))
    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=3))
    rules.update_user(USER_OFFENSES._replace(guild_id=2, user_id=1))

    users = rules.get_users(guild_id=1)
    assert len(users) == 3
    assert {user.user_id for user in users} == {1, 2, 3}

    users = rules.get_users(guild_id=3)
    assert len(users) == 0


def test_add_offense(tmp_file: str) -> None:
    rules = RulesDatabase(db_path=tmp_file)
    rules.update_config(GUILD_CONFIG)

    assert rules.add_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42) == 1
    user = rules.get_user(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    assert user is not None
    assert user.current_offenses == 1
    assert user.total_offenses == 1

    assert rules.add_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42) == 2
    user = rules.get_user(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    assert user is not None
    assert user.current_offenses == 2
    assert user.total_offenses == 2


def test_add_offense_guild_error(tmp_file: str) -> None:
    rules = RulesDatabase(db_path=tmp_file)

    with pytest.raises(GuildNotConfiguredError):
        rules.add_offense(1234, 42)


def test_add_offense_max_offenses(tmp_file: str) -> None:
    rules = RulesDatabase(db_path=tmp_file)
    rules.update_config(GUILD_CONFIG._replace(max_offenses=2))

    rules.add_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    with pytest.raises(MaxOffensesExceededError):
        rules.add_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42)


def test_remove_offense(tmp_file: str) -> None:
    rules = RulesDatabase(db_path=tmp_file)
    rules.update_config(GUILD_CONFIG)

    rules.add_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    rules.remove_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    user = rules.get_user(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    assert user is not None
    assert user.current_offenses == 0
    assert user.total_offenses == 0

    # Should not go negative
    rules.remove_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    user = rules.get_user(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    assert user is not None
    assert user.current_offenses == 0
    assert user.total_offenses == 0

    # Unknown users are no-ops
    rules.remove_offense(guild_id=GUILD_CONFIG.guild_id, user_id=1)


def test_reset_current_offenses(tmp_file: str) -> None:
    rules = RulesDatabase(db_path=tmp_file)
    rules.update_config(GUILD_CONFIG)

    rules.add_offense(guild_id=GUILD_CONFIG.guild_id, user_id=42)

    rules.reset_current_offenses(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    user = rules.get_user(guild_id=GUILD_CONFIG.guild_id, user_id=42)
    assert user is not None
    assert user.current_offenses == 0
    assert user.total_offenses == 1

    # Unknown users are no-ops
    rules.reset_current_offenses(guild_id=GUILD_CONFIG.guild_id, user_id=1)
