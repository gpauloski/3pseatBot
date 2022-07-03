from __future__ import annotations

import json
import os
import pathlib
from typing import Generator

import pytest

from testing.config import EXAMPLE_CONFIG


@pytest.fixture()
def config(tmp_path: pathlib.Path) -> Generator[str, None, None]:
    """Fixture that generates path to valid bot config file."""
    filepath = os.path.join(tmp_path, 'config.json')
    with open(filepath, 'w') as f:
        json.dump(EXAMPLE_CONFIG, f)
    yield filepath
    os.remove(filepath)
