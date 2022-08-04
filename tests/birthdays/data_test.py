from __future__ import annotations

import os
import pathlib

import pytest

from threepseat.birthdays.data import Birthday
from threepseat.birthdays.data import Birthdays
from threepseat.birthdays.data import UnknownBirthdayError


BIRTHDAY = Birthday(
    guild_id=1234,
    user_id=5678,
    author_id=9012,
    creation_time=0,
    birth_day=1,
    birth_month=1,
)


def test_makes_parent_dirs(tmp_path: pathlib.Path) -> None:
    db_parent_path = str(tmp_path / 'dir1' / 'dir2')
    db_path = os.path.join(db_parent_path, 'test.db')
    Birthdays(db_path=db_path)
    assert os.path.isdir(db_parent_path)


def test_birthdays_table_created(tmp_file: str) -> None:
    birthdays = Birthdays(db_path=tmp_file)

    with birthdays.connect() as db:
        res = db.execute(
            'SELECT COUNT(*) FROM sqlite_master '
            'WHERE type="table" AND name="birthdays"',
        ).fetchone()
        assert res[0] == 1


def test_add_get(tmp_file: str) -> None:
    birthdays = Birthdays(db_path=tmp_file)

    birthdays.update(BIRTHDAY)
    assert birthdays.get(BIRTHDAY.guild_id, BIRTHDAY.user_id) == BIRTHDAY


def test_update(tmp_file: str) -> None:
    birthdays = Birthdays(db_path=tmp_file)

    birthdays.update(BIRTHDAY)
    birthdays.update(BIRTHDAY._replace(birth_day=42))
    birthday = birthdays.get(BIRTHDAY.guild_id, BIRTHDAY.user_id)
    assert birthday is not None and birthday.birth_day == 42


def test_all(tmp_file: str) -> None:
    birthdays = Birthdays(db_path=tmp_file)

    birthdays.update(BIRTHDAY._replace(user_id=42))
    birthdays.update(BIRTHDAY._replace(user_id=43))
    birthdays.update(BIRTHDAY._replace(user_id=44))
    birthdays.update(BIRTHDAY._replace(guild_id=1))
    assert len(birthdays.all(BIRTHDAY.guild_id)) == 3


def test_remove(tmp_file: str) -> None:
    birthdays = Birthdays(db_path=tmp_file)

    birthdays.update(BIRTHDAY)
    assert birthdays.get(BIRTHDAY.guild_id, BIRTHDAY.user_id) == BIRTHDAY
    birthdays.remove(BIRTHDAY.guild_id, BIRTHDAY.user_id)
    assert birthdays.get(BIRTHDAY.guild_id, BIRTHDAY.user_id) is None


def test_remove_missing(tmp_file: str) -> None:
    birthdays = Birthdays(db_path=tmp_file)
    with pytest.raises(UnknownBirthdayError):
        birthdays.remove(0, 0)
