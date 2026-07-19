from __future__ import annotations

import contextlib
import functools
import sqlite3
import typing
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Sequence
from pathlib import Path
from types import UnionType
from typing import Any
from typing import Generic
from typing import NamedTuple
from typing import TypeVar

from threepseat.typing import base_type
from threepseat.typing import is_optional

# https://stackoverflow.com/questions/16936608
sqlite3.register_adapter(bool, int)
sqlite3.register_converter(
    'BOOLEAN',
    lambda v: bool(int(v)),  # pragma: no cover
)

BUILTIN_TO_SQLITE = {
    bool: 'BOOLEAN',
    bytes: 'BLOB',
    float: 'REAL',
    int: 'INTEGER',
    str: 'TEXT',
}

RowType = TypeVar('RowType', bound=NamedTuple)


class Field(NamedTuple):
    """Field/column in SQLite3 table."""

    name: str
    python_type: type | UnionType
    sql_type: str


class SQLTableInterface(Generic[RowType]):  # noqa: UP046
    """Abstract interface to a SQLite3 table.

    Table formats are determined using an input RowType.

    Warning:
        This class has not been carefully check for SQL injection attacks so
        use at your own risk.
    """

    def __init__(
        self,
        row_type: type[RowType],
        name: str,
        filepath: str,
        *,
        primary_keys: tuple[str, ...] | None = None,
    ) -> None:
        """Init SQLTableInterface.

        Args:
            row_type (type[RowType]): user defined RowType that represents
                what a row in the table will look like.
            name (str): name of the table to add the the sqlite3 database.
            filepath (str): filepath to the sqlite3 database to use.
            primary_keys (tuple[str]): optional tuple of field names that serve
                as the primary keys for the table. Some operations will
                validate the user provided the primary keys to ensure the
                operation only affects one row. Note: primary keys are not
                officially set in the table because of legacy issues with
                how the tables were previously formatted.

        Raises:
            ValueError:
                if any key in `primary_keys` is not a field of the `row_type`.
        """
        self._row_type = row_type
        self._row_name = row_type.__name__
        self._primary_keys = () if primary_keys is None else primary_keys
        self._name = name
        self._filepath = filepath

        self._field_names = field_names(self._row_type)
        self._fields = field_types(self._row_type)
        self._db: sqlite3.Connection | None = None

        for key in self._primary_keys:
            if key not in self.field_names:
                msg = f'Primary key {key} is not a field in {self._row_name}.'
                raise ValueError(msg)

        parent = Path(self._filepath).parent
        if str(parent) not in ('', '.'):
            parent.mkdir(parents=True, exist_ok=True)

        # Create table
        columns = [
            f'{name} {field.sql_type}' for name, field in self.fields.items()
        ]
        columns_str = ', '.join(columns)
        with self.connect() as db:
            # Table/column names come from the RowType definition, not user
            # input, so this is not susceptible to SQL injection.
            db.execute(
                f'CREATE TABLE IF NOT EXISTS {self.name} ({columns_str})',
            )

        self.all = functools.cache(self._all)
        self.get = functools.cache(self._get)

    @property
    def field_names(self) -> tuple[str, ...]:
        """Returns a tuple of the field/column names in the table."""
        return self._field_names

    @property
    def fields(self) -> dict[str, Field]:
        """Returns dict with information about the types of each field."""
        return self._fields

    @property
    def name(self) -> str:
        """Name of the table in the SQLite3 database."""
        return self._name

    @property
    def primary_keys(self) -> tuple[str, ...]:
        """Tuple of the primary keys."""
        return self._primary_keys

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Database transaction context manager.

        The underlying connection is opened on first use and reused for the
        lifetime of this instance (or until close() is called), so a
        ':memory:' database persists across operations. The context manager
        scopes a transaction, committing on success and rolling back if the
        body raises.
        """
        if self._db is None:
            self._db = sqlite3.connect(self._filepath)
            # Other table instances share this file, so WAL lets them keep
            # reading while this one writes. It is a no-op for ':memory:'.
            self._db.execute('PRAGMA journal_mode=WAL')
        with self._db as db:
            yield db

    def close(self) -> None:
        """Close the database connection.

        Connections are reopened on demand, so this releases the handle
        rather than permanently disabling the table.
        """
        if self._db is not None:
            self._db.close()
            self._db = None

    def validate_kwargs(self, kwargs: dict[str, Any]) -> None:
        """Validate that every key/value in kwargs.

        Specifically checks that each key in kwargs is a field in the table
        and that the type of each value matches the type expected by the
        table.
        """
        for field, value in kwargs.items():
            if field not in self._fields:
                msg = f'Field {field} is not a member of {self._row_name}.'
                raise ValueError(msg)
            if not isinstance(value, self.fields[field].python_type):
                msg = (
                    f'Type of {field} is {type(value)} but expected '
                    f'{self.fields[field].python_type}.'
                )
                # ValueError (not TypeError) is this class's convention for
                # any invalid kwarg, including wrong-typed values.
                raise ValueError(msg)  # noqa: TRY004

    def _all(self, **kwargs: Any) -> list[RowType]:  # noqa: ANN401
        """Get all rows in the table match kwargs."""
        self.validate_kwargs(kwargs)

        where = (
            f'WHERE {fields_to_search_str(kwargs.keys())}'
            if len(kwargs) > 0
            else ''
        )

        with self.connect() as db:
            # Table/column names come from the RowType definition, not user
            # input, so this is not susceptible to SQL injection.
            rows = db.execute(
                f'SELECT * FROM {self.name} {where}',  # noqa: S608
                kwargs,
            ).fetchall()
            return [self._row_type(*row) for row in rows]

    def _get(self, **kwargs: Any) -> RowType | None:  # noqa: ANN401
        """Get the row in the table matching kwargs.

        Raises:
            ValueError:
                if more than one match is found. If this happens, it is
                because the query did not contain all of the primary keys.
        """
        if len(kwargs) == 0:
            msg = 'At least one argument must be provided.'
            raise ValueError(msg)
        self.validate_kwargs(kwargs)

        with self.connect() as db:
            # Table/column names come from the RowType definition, not user
            # input, so this is not susceptible to SQL injection.
            rows = db.execute(
                f'SELECT * FROM {self.name} WHERE '  # noqa: S608
                f'{fields_to_search_str(kwargs.keys())}',
                kwargs,
            ).fetchall()
            if len(rows) == 0:
                return None
            if len(rows) >= 2:  # noqa: PLR2004 (checking for "more than one")
                msg = 'Found multiple matching rows.'
                raise ValueError(msg)
            return self._row_type(*rows[0])

    def update(self, row: RowType) -> None:
        """Update a row in the table or insert it if it does not exist."""
        with self.connect() as db:
            # Table/column names come from the RowType definition, not user
            # input, so this is not susceptible to SQL injection.
            res = db.execute(
                f'UPDATE {self.name} '  # noqa: S608
                f'SET {fields_to_update_str(self.field_names)} '
                f'WHERE {fields_to_search_str(self.primary_keys)}',
                row._asdict(),
            )
            if res.rowcount > 1:
                msg = 'Updated more than one row!'
                raise ValueError(msg)
            if res.rowcount == 0:
                res = db.execute(
                    f'INSERT INTO {self.name} VALUES '  # noqa: S608
                    f'({fields_to_insert_str(self.field_names)})',
                    row._asdict(),
                )

        self.all.cache_clear()
        self.get.cache_clear()

    def remove(self, **kwargs: Any) -> int:  # noqa: ANN401
        """Remove a row from the table.

        Raises:
            ValueError:
                if not all of the primary keys are supplied as kwargs.
        """
        if set(kwargs.keys()) != set(self.primary_keys):
            msg = 'Remove parameters must be the primary keys'
            raise ValueError(msg)
        self.validate_kwargs(kwargs)

        with self.connect() as db:
            # Table/column names come from the RowType definition, not user
            # input, so this is not susceptible to SQL injection.
            res = db.execute(
                f'DELETE FROM {self.name} WHERE '  # noqa: S608
                f'{fields_to_search_str(kwargs.keys())}',
                kwargs,
            )
            changed = res.rowcount

        self.all.cache_clear()
        self.get.cache_clear()
        return changed


def fields_to_update_str(fields: Iterable[str]) -> str:
    """Format field names as a SQL update string.

    Example:
        ('name', 'date', 'kind') -> "name = :name, date = :date, kind = :kind"
    """
    return ', '.join([f'{f} = :{f}' for f in fields])


def fields_to_insert_str(fields: Sequence[str]) -> str:
    """Format field names as a SQL insert string.

    Example:
        ('name', 'date', 'kind') -> ":name, :date, :kind"
    """
    return ', '.join([f':{f}' for f in fields])


def fields_to_search_str(fields: Iterable[str]) -> str:
    """Format field names as a SQL update string.

    Example:
        ('name', 'date', 'kind') ->
            "name = :name ANY date = :date ANY kind = :kind"
    """
    return ' AND '.join([f'{f} = :{f}' for f in fields])


def field_names(nt: NamedTuple | type[NamedTuple]) -> tuple[str, ...]:
    """Get field names of NamedTuple."""
    if not isinstance(nt, type) and hasattr(nt, '__class__'):
        nt = type(nt)
    return tuple(typing.get_type_hints(nt))


def field_types(nt: NamedTuple | type[NamedTuple]) -> dict[str, Field]:
    """Extracts dictionary of field data from NamedTuple."""
    if not isinstance(nt, type) and hasattr(nt, '__class__'):
        nt = type(nt)

    fields: dict[str, Field] = {}

    for name, types in typing.get_type_hints(nt).items():
        if is_optional(types):
            base = base_type(types)
            sql_type = BUILTIN_TO_SQLITE[base]
        else:
            sql_type = BUILTIN_TO_SQLITE[types]
            sql_type = f'{sql_type} NOT NULL'
        fields[name] = Field(name, types, sql_type)

    return fields
