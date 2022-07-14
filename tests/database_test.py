from __future__ import annotations

import sqlite3
from typing import NamedTuple

import pytest

from threepseat.database import create_table
from threepseat.database import named_tuple_fields
from threepseat.database import named_tuple_parameters
from threepseat.database import named_tuple_parameters_update


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


def test_db_create_table_from_named_tuple(
    database: sqlite3.Connection,
) -> None:
    cur = database.cursor()

    class _Row(NamedTuple):
        x: int
        y: str

    create_table(database, 'TestTable', _Row)
    cur.execute(
        f'INSERT INTO TestTable VALUES {named_tuple_parameters(_Row)}',
        _Row(1, 'a')._asdict(),
    )


@pytest.mark.parametrize(
    'fields,expected',
    (
        ([], '()'),
        ([('x', bytes)], '(x BLOB)'),
        ([('x', float)], '(x REAL)'),
        ([('x', int)], '(x INTEGER)'),
        ([('x', str)], '(x TEXT)'),
        ([('c', str), ('b', int), ('a', str)], '(c TEXT, b INTEGER, a TEXT)'),
    ),
)
def test_named_tuple_fields(
    fields: list[tuple[str, type]],
    expected: str,
) -> None:
    tupletype = NamedTuple('TupleType', fields)  # type: ignore
    assert named_tuple_fields(tupletype) == expected


@pytest.mark.parametrize(
    'fields,expected',
    (
        ([], '()'),
        ([('abc', bytes)], '(:abc)'),
        ([('c', str), ('b', int), ('a', str)], '(:c, :b, :a)'),
    ),
)
def test_named_tuple_parameters(
    fields: list[tuple[str, type]],
    expected: str,
) -> None:
    tupletype = NamedTuple('TupleType', fields)  # type: ignore
    assert named_tuple_parameters(tupletype) == expected


@pytest.mark.parametrize(
    'fields,expected',
    (
        ([], ''),
        ([('abc', bytes)], 'abc = :abc'),
        ([('c', str), ('b', int), ('a', str)], 'c = :c, b = :b, a = :a'),
    ),
)
def test_named_tuple_parameters_update(
    fields: list[tuple[str, type]],
    expected: str,
) -> None:
    tupletype = NamedTuple('TupleType', fields)  # type: ignore
    assert named_tuple_parameters_update(tupletype) == expected
