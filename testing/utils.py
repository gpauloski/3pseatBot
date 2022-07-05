from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import uuid
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Generator

import discord.ext.test as dpytest
import pytest
import pytest_asyncio

from testing.config import EXAMPLE_CONFIG
from threepseat.bot import Bot
from threepseat.config import Config


@pytest.fixture()
def tmp_file(tmp_path: pathlib.Path) -> Generator[str, None, None]:
    """Fixture that random file path."""
    filepath = os.path.join(tmp_path, str(uuid.uuid4()))
    yield filepath
    os.remove(filepath)


@pytest_asyncio.fixture
@pytest.mark.asyncio
async def bot(tmp_file) -> Bot:
    """Fixture that initialized bot instance."""
    cfg = EXAMPLE_CONFIG.copy()
    cfg['sqlite_database'] = tmp_file
    bot = Bot(Config(**cfg))  # type: ignore
    dpytest.configure(bot)
    return bot


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
