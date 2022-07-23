from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import uuid
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Generator
from typing import Any
from unittest import mock

import pytest

from testing.config import EXAMPLE_CONFIG


@pytest.fixture()
def tmp_file(tmp_path: pathlib.Path) -> Generator[str, None, None]:
    """Fixture that random file path."""
    filepath = os.path.join(tmp_path, str(uuid.uuid4()))
    yield filepath
    if os.path.exists(filepath):  # pragma: no branch
        os.remove(filepath)


@pytest.fixture()
def database() -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(':memory:')
    yield con
    con.close()


@pytest.fixture()
def config(tmp_path: pathlib.Path) -> Generator[str, None, None]:
    """Fixture that generates path to valid bot config file."""
    filepath = os.path.join(tmp_path, 'config.json')
    with open(filepath, 'w') as f:
        json.dump(EXAMPLE_CONFIG, f)
    yield filepath
    os.remove(filepath)


def extract(app_command) -> Callable[..., Awaitable[Any]]:
    """Extract the original function from the Command."""
    return app_command._callback


@pytest.fixture()
def mock_download() -> Generator[None, None, None]:
    def _download(link: str, filepath: str) -> None:
        with open(filepath, 'w') as f:
            f.write('data')

    with mock.patch(
        'threepseat.sounds.data.download',
        mock.MagicMock(side_effect=_download),
    ):
        yield
