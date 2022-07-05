from __future__ import annotations

import sqlite3


def create_table(
    con: sqlite3.Connection,
    table: str,
    values: str,
) -> None:
    """Creates the table if it does not exist."""
    cur = con.cursor()
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table} {values}')
    con.commit()
