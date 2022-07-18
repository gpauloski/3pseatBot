from __future__ import annotations

import os
import pathlib

from threepseat.rules.data import GuildConfig
from threepseat.rules.data import Rules
from threepseat.rules.data import UserOffenses

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


def test_makes_parent_dirs(tmp_path: pathlib.Path) -> None:
    db_parent_path = str(tmp_path / 'dir1' / 'dir2')
    db_path = os.path.join(db_parent_path, 'test.db')
    Rules(db_path=db_path)
    assert os.path.isdir(db_parent_path)


def test_configs_table_created(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    with rules.connect() as db:
        res = db.execute(
            'SELECT COUNT(*) FROM sqlite_master '
            'WHERE type="table" AND name="guild_configs"',
        ).fetchone()
        assert res[0] == 1


def test_user_offenses_table_created(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    with rules.connect() as db:
        res = db.execute(
            'SELECT COUNT(*) FROM sqlite_master '
            'WHERE type="table" AND name="user_offenses"',
        ).fetchone()
        assert res[0] == 1


def test_config(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    config = GUILD_CONFIG._replace(guild_id=1)
    rules.update_config(config)
    found_config = rules.get_config(guild_id=1)
    assert config == found_config

    config = GUILD_CONFIG._replace(guild_id=2)
    rules.update_config(config)
    found_config = rules.get_config(guild_id=2)
    assert config == found_config

    assert rules.get_config(guild_id=3) is None


def test_update_config(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    config = GUILD_CONFIG._replace(guild_id=1)
    rules.update_config(config)

    with rules.connect() as db:
        rows = db.execute(
            'SELECT * FROM guild_configs '
            'WHERE guild_id = 1 AND max_offenses = 3',
        ).fetchall()
        assert len(rows) == 1

    rules.update_config(config._replace(max_offenses=5))

    with rules.connect() as db:
        rows = db.execute(
            'SELECT * FROM guild_configs'
            ' WHERE guild_id = 1 AND max_offenses = 3',
        ).fetchall()
        assert len(rows) == 0

        rows = db.execute(
            'SELECT * FROM guild_configs '
            'WHERE guild_id = 1 AND max_offenses = 5',
        ).fetchall()
        assert len(rows) == 1


def test_get_configs(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    assert len(rules.get_configs()) == 0

    rules.update_config(GUILD_CONFIG._replace(guild_id=1))
    rules.update_config(GUILD_CONFIG._replace(guild_id=2))
    rules.update_config(GUILD_CONFIG._replace(guild_id=3))
    rules.update_config(GUILD_CONFIG._replace(guild_id=4))

    configs = rules.get_configs()
    assert len(configs) == 4
    assert {config.guild_id for config in configs} == {1, 2, 3, 4}


def test_user(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    user = USER_OFFENSES._replace(user_id=1)
    rules.update_user(user)
    found_user = rules.get_user(guild_id=1234, user_id=1)
    assert user == found_user

    user = USER_OFFENSES._replace(user_id=2)
    rules.update_user(user)
    found_user = rules.get_user(guild_id=1234, user_id=2)
    assert user == found_user

    assert rules.get_user(guild_id=1, user_id=1) is None


def test_update_user(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    user = USER_OFFENSES._replace(guild_id=5678, user_id=1)
    rules.update_user(user)

    with rules.connect() as db:
        rows = db.execute(
            'SELECT * FROM user_offenses '
            'WHERE guild_id = 5678 AND user_id = 1 AND current_offenses = 0',
        ).fetchall()
        assert len(rows) == 1

    rules.update_user(user._replace(current_offenses=1))

    with rules.connect() as db:
        rows = db.execute(
            'SELECT * FROM user_offenses '
            'WHERE guild_id = 5678 AND user_id = 1 AND current_offenses = 0',
        ).fetchall()
        assert len(rows) == 0

        rows = db.execute(
            'SELECT * FROM user_offenses '
            'WHERE guild_id = 5678 AND user_id = 1 AND current_offenses = 1',
        ).fetchall()
        assert len(rows) == 1


def test_get_users(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=1))
    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=2))
    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=3))
    rules.update_user(USER_OFFENSES._replace(guild_id=2, user_id=1))

    users = rules.get_users(guild_id=1)
    assert len(users) == 3
    assert {user.user_id for user in users} == {1, 2, 3}

    users = rules.get_users(guild_id=3)
    assert len(users) == 0


def test_cached_get_config(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    rules.update_config(GUILD_CONFIG._replace(guild_id=1))
    rules.get_config(guild_id=1)
    assert rules.get_config.cache_info().misses == 1
    assert rules.get_config.cache_info().hits == 0

    rules.get_config(guild_id=1)
    assert rules.get_config.cache_info().misses == 1
    assert rules.get_config.cache_info().hits == 1


def test_cached_get_user(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=1))
    rules.get_user(guild_id=1, user_id=1)
    assert rules.get_user.cache_info().misses == 1
    assert rules.get_user.cache_info().hits == 0

    rules.get_user(guild_id=1, user_id=1)
    assert rules.get_user.cache_info().misses == 1
    assert rules.get_user.cache_info().hits == 1


def test_cached_get_users(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=1))
    rules.get_users(guild_id=1)
    assert rules.get_users.cache_info().misses == 1
    assert rules.get_users.cache_info().hits == 0

    rules.get_users(guild_id=1)
    assert rules.get_users.cache_info().misses == 1
    assert rules.get_users.cache_info().hits == 1


def test_update_config_resets_cache(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    rules.update_config(GUILD_CONFIG._replace(guild_id=1))
    rules.get_config(guild_id=1)
    assert rules.get_config.cache_info().misses == 1
    assert rules.get_config.cache_info().hits == 0

    rules.get_config(guild_id=1)
    assert rules.get_config.cache_info().misses == 1
    assert rules.get_config.cache_info().hits == 1

    rules.get_configs()
    assert rules.get_configs.cache_info().misses == 1
    assert rules.get_configs.cache_info().hits == 0

    rules.get_configs()
    assert rules.get_configs.cache_info().misses == 1
    assert rules.get_configs.cache_info().hits == 1

    config = GUILD_CONFIG._replace(guild_id=1, max_offenses=42)
    rules.update_config(config)

    rules.get_config(guild_id=1)
    assert rules.get_config.cache_info().misses == 1
    assert rules.get_config.cache_info().hits == 0

    rules.get_configs()
    assert rules.get_configs.cache_info().misses == 1
    assert rules.get_configs.cache_info().hits == 0


def test_update_user_resets_caches(tmp_file: str) -> None:
    rules = Rules(db_path=tmp_file)

    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=1))
    rules.get_user(guild_id=1, user_id=1)
    assert rules.get_user.cache_info().misses == 1
    assert rules.get_user.cache_info().hits == 0

    rules.get_user(guild_id=1, user_id=1)
    assert rules.get_user.cache_info().misses == 1
    assert rules.get_user.cache_info().hits == 1

    rules.get_users(guild_id=1)
    assert rules.get_users.cache_info().misses == 1
    assert rules.get_users.cache_info().hits == 0

    rules.get_users(guild_id=1)
    assert rules.get_users.cache_info().misses == 1
    assert rules.get_users.cache_info().hits == 1

    # Updating users should invalidate caches
    rules.update_user(USER_OFFENSES._replace(guild_id=1, user_id=2))

    rules.get_user(guild_id=1, user_id=1)
    assert rules.get_user.cache_info().misses == 1
    assert rules.get_user.cache_info().hits == 0

    rules.get_users(guild_id=1)
    assert rules.get_users.cache_info().misses == 1
    assert rules.get_users.cache_info().hits == 0
