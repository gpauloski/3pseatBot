from __future__ import annotations

import json
import os
import pathlib
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


@pytest_asyncio.fixture
@pytest.mark.asyncio
async def bot() -> Bot:
    """Fixture that initialized bot instance."""
    bot = Bot(Config(**EXAMPLE_CONFIG))  # type: ignore
    dpytest.configure(bot)
    return bot


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
