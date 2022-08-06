from __future__ import annotations

import os
import pathlib
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Sequence
from typing import NamedTuple

import pytest

from threepseat.table import Field
from threepseat.table import field_names
from threepseat.table import field_types
from threepseat.table import fields_to_insert_str
from threepseat.table import fields_to_search_str
from threepseat.table import fields_to_update_str
from threepseat.table import SQLTableInterface


class ExampleRow(NamedTuple):
    guild_id: int
    user_id: int
    timestamp: float
    filepath: str | None
    admin: bool


@pytest.fixture
def table(
    tmp_file: str,
) -> Generator[SQLTableInterface[ExampleRow], None, None]:
    yield SQLTableInterface(
        ExampleRow,
        'mytable',
        tmp_file,
        primary_keys=('guild_id', 'user_id'),
    )


def test_table_init(tmp_file) -> None:
    table = SQLTableInterface(ExampleRow, 'mytable', tmp_file)

    # Check mytable is created
    with table.connect() as db:
        res = db.execute(
            'SELECT COUNT(*) FROM sqlite_master '
            'WHERE type="table" AND name="mytable"',
        ).fetchone()
        assert res[0] == 1


def test_table_init_primary_keys_valid() -> None:
    SQLTableInterface(
        ExampleRow,
        'mytable',
        ':memory:',
        primary_keys=('guild_id',),
    )
    with pytest.raises(ValueError, match='is not a field'):
        SQLTableInterface(
            ExampleRow,
            'mytable',
            ':memory:',
            primary_keys=('missing_field',),
        )


def test_makes_parent_dirs(tmp_path: pathlib.Path) -> None:
    db_parent_path = str(tmp_path / 'dir1' / 'dir2')
    db_path = os.path.join(db_parent_path, 'test.db')
    SQLTableInterface(ExampleRow, 'mytable', db_path)
    assert os.path.isdir(db_parent_path)


def test_validate_kwargs() -> None:
    table = SQLTableInterface(ExampleRow, 'mytable', ':memory:')

    table.validate_kwargs({})
    table.validate_kwargs({'guild_id': 1})
    table.validate_kwargs({'guild_id': 1, 'filepath': None})

    with pytest.raises(ValueError, match='not a member'):
        table.validate_kwargs(
            {'guild_id': 1, 'filepath': None, 'missing': int},
        )

    with pytest.raises(ValueError, match='expected'):
        table.validate_kwargs({'guild_id': 'not an int'})


def test_add_get(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)
    table.update(row)
    assert table.get(guild_id=0, user_id=0) == row


def test_get_with_no_params(table) -> None:
    with pytest.raises(ValueError, match='At least one argument'):
        table.get()


def test_get_multiple_values(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)
    table.update(row)

    # Manually add second row with same values
    with table.connect() as db:
        db.execute(f'INSERT INTO {table.name} VALUES (0, 0, 0.0, NULL, 0)')

    with pytest.raises(ValueError, match='Found multiple matching rows'):
        table.get(user_id=0)


def test_update(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    table.update(row._replace(timestamp=1.0))
    result = table.get(guild_id=row.guild_id, user_id=row.user_id)
    assert result is not None and result.timestamp == 1.0

    table.update(row._replace(timestamp=2.0))
    result = table.get(guild_id=row.guild_id, user_id=row.user_id)
    assert result is not None and result.timestamp == 2.0


def test_update_multiple_rows(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    table.update(row)
    # Manually add second row with same values
    with table.connect() as db:
        db.execute(f'INSERT INTO {table.name} VALUES (0, 0, 0.0, NULL, 1)')

    with pytest.raises(ValueError, match='Updated more than one row!'):
        table.update(row._replace(admin=False))


def test_all(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    table.update(row._replace(user_id=1))
    table.update(row._replace(user_id=2))
    table.update(row._replace(user_id=3))
    table.update(row._replace(guild_id=1))

    rows = table.all()
    assert len(rows) == 4
    assert all(isinstance(row, ExampleRow) for row in rows)

    rows = table.all(guild_id=0)
    assert len(rows) == 3


def test_remove(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    assert table.remove(guild_id=row.guild_id, user_id=row.user_id) == 0

    table.update(row)
    assert table.get(guild_id=row.guild_id, user_id=row.user_id)
    n = table.remove(guild_id=row.guild_id, user_id=row.user_id)
    assert n == 1
    assert table.get(guild_id=row.guild_id, user_id=row.user_id) is None

    assert len(table.all()) == 0
    table.update(row)
    # Manually add second row
    with table.connect() as db:
        db.execute(f'INSERT INTO {table.name} VALUES (0, 0, 0.0, NULL, 0)')

    assert table.remove(guild_id=row.guild_id, user_id=row.user_id) == 2


def test_remove_without_primary_keys(table) -> None:
    with pytest.raises(ValueError, match='must be the primary keys'):
        table.remove()

    with pytest.raises(ValueError, match='must be the primary keys'):
        table.remove(guild_id=0, user_id=0, timestamp=0.0)


def test_get_caching(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    table.update(row)
    assert table.get.cache_info().hits == 0
    assert table.get.cache_info().misses == 0

    table.get(guild_id=0, user_id=0)
    assert table.get.cache_info().hits == 0
    assert table.get.cache_info().misses == 1

    table.get(guild_id=0, user_id=0)
    assert table.get.cache_info().hits == 1
    assert table.get.cache_info().misses == 1


def test_all_caching(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    table.update(row)
    assert table.all.cache_info().hits == 0
    assert table.all.cache_info().misses == 0

    table.all(guild_id=0)
    assert table.all.cache_info().hits == 0
    assert table.all.cache_info().misses == 1

    table.all(guild_id=0)
    assert table.all.cache_info().hits == 1
    assert table.all.cache_info().misses == 1


def test_update_resets_cache(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    table.update(row)
    assert table.get.cache_info().misses == 0

    table.get(guild_id=0, user_id=0)
    assert table.get.cache_info().misses == 1

    table.all(guild_id=0)
    assert table.all.cache_info().misses == 1

    table.update(row._replace(timestamp=1.0))
    assert table.get.cache_info().misses == 0
    assert table.all.cache_info().misses == 0


def test_remove_resets_cache(table) -> None:
    row = ExampleRow(0, 0, 0.0, None, True)

    table.update(row)
    assert table.get.cache_info().misses == 0

    table.get(guild_id=0, user_id=0)
    assert table.get.cache_info().misses == 1

    table.all(guild_id=0)
    assert table.all.cache_info().misses == 1

    table.remove(guild_id=0, user_id=0)
    assert table.get.cache_info().misses == 0
    assert table.all.cache_info().misses == 0


@pytest.mark.parametrize(
    'fields,result',
    (
        ([], ''),
        (['name'], 'name = :name'),
        (['name', 'date'], 'name = :name, date = :date'),
        (
            ['name', 'date', 'phone'],
            'name = :name, date = :date, phone = :phone',
        ),
    ),
)
def test_fields_to_update_str(fields: Iterable[str], result: str) -> None:
    assert fields_to_update_str(fields) == result


@pytest.mark.parametrize(
    'fields,result',
    (
        ([], ''),
        (['name'], ':name'),
        (['name', 'date'], ':name, :date'),
        (['name', 'date', 'phone'], ':name, :date, :phone'),
    ),
)
def test_fields_to_insert_str(fields: Sequence[str], result: str) -> None:
    assert fields_to_insert_str(fields) == result


@pytest.mark.parametrize(
    'fields,result',
    (
        ([], ''),
        (['name'], 'name = :name'),
        (['name', 'date'], 'name = :name AND date = :date'),
        (
            ['name', 'date', 'phone'],
            'name = :name AND date = :date AND phone = :phone',
        ),
    ),
)
def test_fields_to_search_str(fields: Iterable[str], result: str) -> None:
    assert fields_to_search_str(fields) == result


def test_field_names() -> None:
    expected = ('guild_id', 'user_id', 'timestamp', 'filepath', 'admin')
    assert field_names(ExampleRow) == expected
    assert field_names(ExampleRow(1, 1, 1.0, None, True)) == expected


def test_field_types() -> None:
    expected = {
        'bool_type': Field('bool_type', bool, 'BOOLEAN NOT NULL'),
        'bytes_type': Field('bytes_type', bytes, 'BLOB NOT NULL'),
        'float_type': Field('float_type', float, 'REAL NOT NULL'),
        'int_type': Field('int_type', int, 'INTEGER NOT NULL'),
        'str_type': Field('str_type', str, 'TEXT NOT NULL'),
        'bool_opt_type': Field('bool_opt_type', bool | None, 'BOOLEAN'),
        'bytes_opt_type': Field('bytes_opt_type', bytes | None, 'BLOB'),
        'float_opt_type': Field('float_opt_type', float | None, 'REAL'),
        'int_opt_type': Field('int_opt_type', int | None, 'INTEGER'),
        'str_opt_type': Field('str_opt_type', str | None, 'TEXT'),
    }

    class _AllTypesRow(NamedTuple):
        bool_type: bool
        bytes_type: bytes
        float_type: float
        int_type: int
        str_type: str
        bool_opt_type: bool | None
        bytes_opt_type: bytes | None
        float_opt_type: float | None
        int_opt_type: int | None
        str_opt_type: str | None

    found_type = field_types(_AllTypesRow)
    found_instance = field_types(
        _AllTypesRow(True, b'', 0.0, 0, '', None, None, None, None, None),
    )
    assert len(expected) == len(found_type) == len(found_instance)
    for field in expected:
        assert expected[field] == found_type[field] == found_instance[field]
