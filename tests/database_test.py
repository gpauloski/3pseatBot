from __future__ import annotations

import sqlite3

from threepseat.database import create_table


def test_db_create_table(database: sqlite3.Connection) -> None:
    cur = database.cursor()

    def _exists(table: str) -> bool:
        cur.execute(
            'SELECT COUNT(*) FROM sqlite_master '
            'WHERE type="table" AND name=:table',
            {'table': table},
        )
        return cur.fetchone()[0] == 1

    def _rows(table: str) -> int:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        return cur.fetchone()[0]

    name = 'testtable'
    values = '(id INTEGER, name TEXT)'

    assert not _exists(name)
    create_table(database, name, values)
    assert _exists(name)
    cur.execute(
        f'INSERT INTO {name} VALUES (:id, :name)',
        {'id': 1234, 'name': 'alice'},
    )
    # Make sure table is not overwritten
    assert _rows(name) == 1
    create_table(database, name, values)
    assert _rows(name) == 1
