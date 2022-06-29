from __future__ import annotations

import subprocess

import pytest

import threepseat
from threepseat.main import main


def test_main() -> None:
    main([])


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


def test_cli() -> None:
    result = subprocess.run(
        ['threepseatbot', '--version'],
        capture_output=True,
    )
    assert result.returncode == 0
    assert threepseat.__version__ in str(result.stdout)
