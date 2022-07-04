from __future__ import annotations

import contextlib
import logging
import pathlib
import shutil
import subprocess
from unittest import mock

import pytest

import threepseat
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


def test_main_start(config: str) -> None:
    # Note: we are not interested in testing the functionality of the bot here,
    # just that it gets started
    with mock.patch('threepseat.main.Bot', autospec=True) as mocked:
        assert not mocked.called
        with contextlib.redirect_stdout(None):
            main(['--config', str(config)])
        assert mocked.called


def test_main_errors(config: str, caplog) -> None:
    caplog.set_level(logging.ERROR)
    with mock.patch(
        'threepseat.main.amain',
        mock.AsyncMock(side_effect=KeyboardInterrupt),
    ):
        ret = main(['--config', config])
    assert ret == 0

    with mock.patch(
        'threepseat.main.amain',
        mock.AsyncMock(side_effect=Exception('uh oh')),
    ):
        ret = main(['--config', config])
    assert ret != 0
    assert any(['uh oh' in record.message for record in caplog.records])


def test_logging(config: str, tmp_path: pathlib.Path) -> None:
    logdir = tmp_path / 'logdir'
    if logdir.exists():  # pragma: no cover
        shutil.rmtree(logdir)
    with mock.patch('threepseat.main.amain', mock.AsyncMock()):
        main(['--config', config, '--log-dir', str(logdir)])
    assert logdir.exists()
    shutil.rmtree(logdir)


def test_cli() -> None:
    result = subprocess.run(
        ['threepseatbot', '--version'],
        capture_output=True,
    )
    assert result.returncode == 0
    assert threepseat.__version__ in str(result.stdout)
