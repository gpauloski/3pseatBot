from __future__ import annotations

import asyncio
import contextlib
import logging
import pathlib
import shutil
import subprocess
from typing import Any
from unittest import mock

import pytest

import threepseat
from testing.config import TEMPLATE_CONFIG
from threepseat.main import amain
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
    with filepath.open() as f:
        assert f.read() == TEMPLATE_CONFIG


def test_main_start(config: str) -> None:
    # Note: we are not interested in testing the functionality of the bot here,
    # just that it gets started
    with (
        # mock.patch('threepseat.main.Bot', autospec=True) as mocked_bot,
        # mock.patch('quart.Quart', autospec=True) as mocked_app
        mock.patch(
            'threepseat.main.Bot.start',
            mock.AsyncMock(),
        ) as mocked_bot,
        mock.patch('quart.Quart.run_task', mock.AsyncMock()) as mocked_app,
    ):
        assert not mocked_bot.called
        assert not mocked_app.called
        with contextlib.redirect_stdout(None):
            main(['--config', str(config)])
        assert mocked_bot.called
        assert mocked_app.called


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
    assert 'uh oh' in caplog.text


def test_logging(config: str, tmp_path: pathlib.Path) -> None:
    logdir = tmp_path / 'logdir'
    if logdir.exists():  # pragma: no cover
        shutil.rmtree(logdir)
    with mock.patch('threepseat.main.amain', mock.AsyncMock()):
        main(['--config', config, '--log-dir', str(logdir)])
    assert logdir.exists()
    shutil.rmtree(logdir)


def test_cli() -> None:
    result = subprocess.run(  # noqa: PLW1510
        ['threepseatbot', '--version'],  # noqa: S607
        capture_output=True,
    )
    assert result.returncode == 0


@pytest.mark.asyncio
async def test_amain_shutdown_trigger(config: str) -> None:
    shutdown_event = asyncio.Event()
    triggers: list[Any] = []

    # Patched onto the class, so this receives the Quart app as self.
    async def _run_task(_self: Any, **kwargs: Any) -> None:
        triggers.append(kwargs['shutdown_trigger'])

    with (
        mock.patch('threepseat.main.Bot.start', mock.AsyncMock()),
        mock.patch('quart.Quart.run_task', _run_task),
    ):
        await amain(threepseat.config.load(config), shutdown_event)

    # The wrapper handed to hypercorn resolves once the event is set.
    (trigger,) = triggers
    shutdown_event.set()
    assert await trigger() is None


@pytest.mark.asyncio
async def test_amain_surfaces_service_error(config: str, caplog) -> None:
    caplog.set_level(logging.ERROR)
    with (
        mock.patch(
            'threepseat.main.Bot.start',
            mock.AsyncMock(side_effect=asyncio.CancelledError),
        ),
        mock.patch(
            'quart.Quart.run_task',
            mock.AsyncMock(side_effect=RuntimeError('webapp died')),
        ),
        pytest.raises(RuntimeError, match='webapp died'),
    ):
        await amain(threepseat.config.load(config), asyncio.Event())

    # A clean shutdown (CancelledError) is not reported as a failure.
    assert any('webapp exited' in record.message for record in caplog.records)
    assert not any('bot exited' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_amain_surfaces_first_of_many_errors(
    config: str,
    caplog,
) -> None:
    caplog.set_level(logging.ERROR)
    with (
        mock.patch(
            'threepseat.main.Bot.start',
            mock.AsyncMock(side_effect=RuntimeError('bot died')),
        ),
        mock.patch(
            'quart.Quart.run_task',
            mock.AsyncMock(side_effect=RuntimeError('webapp died')),
        ),
        # Both services failed, but only the first is raised.
        pytest.raises(RuntimeError, match='bot died'),
    ):
        await amain(threepseat.config.load(config), asyncio.Event())

    assert any('bot exited' in record.message for record in caplog.records)
    assert any('webapp exited' in record.message for record in caplog.records)
