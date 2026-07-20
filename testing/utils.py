from __future__ import annotations

import asyncio
import json
import pathlib
import time
import uuid
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Generator
from typing import Any
from typing import cast
from unittest import mock

import pytest
from discord import app_commands

from testing.config import EXAMPLE_CONFIG


@pytest.fixture
def tmp_file(tmp_path: pathlib.Path) -> str:
    """Fixture that returns a random file path."""
    # tmp_path is removed by pytest, so nothing to clean up here.
    return str(tmp_path / str(uuid.uuid4()))


@pytest.fixture
def config(tmp_path: pathlib.Path) -> str:
    """Fixture that generates path to valid bot config file."""
    filepath = tmp_path / 'config.json'
    with filepath.open('w') as f:
        json.dump(EXAMPLE_CONFIG, f)
    return str(filepath)


async def wait_for(
    predicate: Callable[[], bool],
    max_wait: float = 5.0,
    interval: float = 0.01,
) -> None:
    """Wait for a background task to make the predicate true."""
    deadline = time.monotonic() + max_wait
    while not predicate():
        if time.monotonic() > deadline:  # pragma: no cover
            msg = 'Timeout waiting for condition to become true.'
            raise TimeoutError(msg)
        await asyncio.sleep(interval)


def extract(
    app_command: app_commands.Command[Any, ..., Any],
) -> Callable[..., Awaitable[Any]]:
    """Extract the original function from the Command."""
    return cast('Callable[..., Awaitable[Any]]', app_command._callback)


@pytest.fixture
def mock_download() -> Generator[None, None, None]:
    def _download(link: str, filepath: str) -> None:
        with pathlib.Path(filepath).open('w') as f:
            f.write('data')

    with mock.patch(
        'threepseat.ext.sounds.commands.download',
        mock.MagicMock(side_effect=_download),
    ):
        yield
