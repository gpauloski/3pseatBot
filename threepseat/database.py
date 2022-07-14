from __future__ import annotations

import sqlite3
from typing import get_type_hints
from typing import NamedTuple


BUILTIN_TO_SQLITE = {
    bytes: 'BLOB',
    float: 'REAL',
    int: 'INTEGER',
    str: 'TEXT',
}


def create_table(
    con: sqlite3.Connection,
    table: str,
    values: str | type[NamedTuple],
) -> None:
    """Creates the table if it does not exist."""
    cur = con.cursor()
    if isinstance(values, str):
        values_str = values
    else:
        values_str = named_tuple_fields(values)
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table} {values_str}')
    con.commit()


def named_tuple_fields(namedtuple: type[NamedTuple]) -> str:
    """Convert fields of NamedTuple type to list of table fields.

    Args:
        namedtuple (type[NamedTuple]): named tuple to parse.

    Returns:
        string with field and types of the named tuple listed in
        format for creating a SQL table.

    Raises:
        KeyError:
            named tuple has a type that is not supported.
    """
    table_values: list[str] = []
    for field_name, field_type in get_type_hints(namedtuple).items():
        table_values.append(f'{field_name} {BUILTIN_TO_SQLITE[field_type]}')
    table_values_str = ', '.join(table_values)
    return f'({table_values_str})'


def named_tuple_parameters(namedtuple: type[NamedTuple]) -> str:
    """Convert fields of NamedTuple type to sqlite3 parameters.

    Args:
        namedtuple (type[NamedTuple]): named tuple to extract parameters of.

    Returns:
        string of fields in format of sqlite3 parameters.
    """
    params: list[str] = []
    for field_name in get_type_hints(namedtuple):
        params.append(f':{field_name}')
    params_str = ', '.join(params)
    return f'({params_str})'


def named_tuple_parameters_update(namedtuple: type[NamedTuple]) -> str:
    """Convert fields of NamedTuple type to sqlite3 update records.

    Args:
        namedtuple (type[NamedTuple]): named tuple to extract parameters of.

    Returns:
        string of fields in format for sqlite3 update statement.
    """
    params: list[str] = []
    for field_name in get_type_hints(namedtuple):
        params.append(f'{field_name} = :{field_name}')
    return ', '.join(params)
