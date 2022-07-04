from __future__ import annotations

import json
import pathlib

import pytest

from testing.config import EXAMPLE_CONFIG
from testing.config import TEMPLATE_CONFIG
from threepseat.config import Config
from threepseat.config import load
from threepseat.config import write_template


def test_config_parse_correct() -> None:
    cfg = Config(**EXAMPLE_CONFIG)  # type: ignore
    for field, value in EXAMPLE_CONFIG.items():
        assert getattr(cfg, field) == value
        assert isinstance(getattr(cfg, field), type(value))


def test_config_parse_bad_types() -> None:
    cfg_dict = {
        'bot_token': '1234',
        'client_id': 1234,
        # This should be a string
        'client_secret': 1234,
        'sqlite_database': 'str',
    }
    with pytest.raises(
        TypeError,
        match=(
            'Expected type \'str\' for Config field \'client_secret\' '
            'but got type \'int\'.'
        ),
    ):
        Config(**cfg_dict)  # type: ignore


def test_secret_not_in_repr() -> None:
    cfg = Config(**EXAMPLE_CONFIG)  # type: ignore
    r = repr(cfg)
    for field in EXAMPLE_CONFIG:
        if field not in ('client_secret', 'bot_token'):
            assert field in r
        else:
            assert field not in r


def test_config_template() -> None:
    assert Config.template() == TEMPLATE_CONFIG


def test_load_config(tmp_path: pathlib.Path) -> None:
    filepath = tmp_path / 'config.json'
    with open(filepath, 'w') as f:
        json.dump(EXAMPLE_CONFIG, f)

    cfg = load(str(filepath))
    assert cfg == Config(**EXAMPLE_CONFIG)  # type: ignore


def test_write_template(tmp_path: pathlib.Path) -> None:
    filepath = tmp_path / 'template.json'
    write_template(str(filepath))

    with open(filepath) as f:
        assert f.read() == TEMPLATE_CONFIG
