from __future__ import annotations

import os
import pathlib

import pytest

from threepseat.reminders.data import Reminder
from threepseat.reminders.data import Reminders
from threepseat.reminders.data import UnknownReminderError


VOICE_REMINDER = Reminder(
    guild_id=1234,
    channel_id=5678,
    author_id=9012,
    creation_time=0,
    name='test',
    text='test message',
    delay_minutes=1,
)


def test_makes_parent_dirs(tmp_path: pathlib.Path) -> None:
    db_parent_path = str(tmp_path / 'dir1' / 'dir2')
    db_path = os.path.join(db_parent_path, 'test.db')
    Reminders(db_path=db_path)
    assert os.path.isdir(db_parent_path)


def test_reminders_table_created(tmp_file: str) -> None:
    reminders = Reminders(db_path=tmp_file)

    with reminders.connect() as db:
        res = db.execute(
            'SELECT COUNT(*) FROM sqlite_master '
            'WHERE type="table" AND name="reminders"',
        ).fetchone()
        assert res[0] == 1


def test_add_get(tmp_file: str) -> None:
    reminders = Reminders(db_path=tmp_file)

    reminders.update(VOICE_REMINDER)
    assert (
        reminders.get(VOICE_REMINDER.guild_id, VOICE_REMINDER.name)
        == VOICE_REMINDER
    )


def test_update(tmp_file: str) -> None:
    reminders = Reminders(db_path=tmp_file)

    reminders.update(VOICE_REMINDER)
    reminders.update(VOICE_REMINDER._replace(text='new message'))
    reminder = reminders.get(VOICE_REMINDER.guild_id, VOICE_REMINDER.name)
    assert reminder is not None and reminder.text == 'new message'


def test_all(tmp_file: str) -> None:
    reminders = Reminders(db_path=tmp_file)

    reminders.update(VOICE_REMINDER._replace(name='a'))
    reminders.update(VOICE_REMINDER._replace(name='b'))
    reminders.update(VOICE_REMINDER._replace(name='c'))
    reminders.update(VOICE_REMINDER._replace(guild_id=1))
    assert len(reminders.all(VOICE_REMINDER.guild_id)) == 3


def test_remove(tmp_file: str) -> None:
    reminders = Reminders(db_path=tmp_file)

    reminders.update(VOICE_REMINDER)
    assert (
        reminders.get(VOICE_REMINDER.guild_id, VOICE_REMINDER.name)
        == VOICE_REMINDER
    )
    reminders.remove(VOICE_REMINDER.guild_id, VOICE_REMINDER.name)
    assert reminders.get(VOICE_REMINDER.guild_id, VOICE_REMINDER.name) is None


def test_remove_missing(tmp_file: str) -> None:
    reminders = Reminders(db_path=tmp_file)
    with pytest.raises(UnknownReminderError):
        reminders.remove(0, 'test')
