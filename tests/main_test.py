from __future__ import annotations

import contextlib
import json
import pathlib
import subprocess

import pytest

import threepseat
from testing.config import EXAMPLE_CONFIG
from testing.config import TEMPLATE_CONFIG
from threepseat.main import main


def test_main_no_args_raises_help(capsys) -> None:
    with pytest.raises(SystemExit):
        main([])
    out, _ = capsys.readouterr()
    assert '--help' in out


def test_main_help(capsys) -> None:
    with pytest.raises(SystemExit) as e:
        main(['--help'])
    assert e.value.code == 0
    out, _ = capsys.readouterr()
    assert '--help' in out
    assert '--version' in out


def test_main_version(capsys) -> None:
    with pytest.raises(SystemExit) as e:
        main(['--version'])
    assert e.value.code == 0
    out, _ = capsys.readouterr()
    assert threepseat.__version__ in out


def test_main_template(tmp_path: pathlib.Path) -> None:
    filepath = tmp_path / 'template.json'
    retcode = main(['--template', str(filepath)])
    assert retcode == 0
    with open(filepath) as f:
        assert f.read() == TEMPLATE_CONFIG


def test_main_start(tmp_path: pathlib.Path) -> None:
    filepath = tmp_path / 'config.json'
    with open(filepath, 'w') as f:
        json.dump(EXAMPLE_CONFIG, f)
    with contextlib.redirect_stdout(None):
        main(['--config', str(filepath)])


def test_cli() -> None:
    result = subprocess.run(
        ['threepseatbot', '--version'],
        capture_output=True,
    )
    assert result.returncode == 0
    assert threepseat.__version__ in str(result.stdout)
