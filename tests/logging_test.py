from __future__ import annotations

import logging
import pathlib
import time

import pytest

from threepseat.logging import _NOISY_LOGGERS
from threepseat.logging import configure_logging
from threepseat.logging import log_timing

logger = logging.getLogger(__name__)


def test_configure_logging_uses_local_time() -> None:
    configure_logging(logdir=None, level='INFO')
    assert logging.Formatter.converter is time.localtime


def test_configure_logging_creates_log_dir(
    tmp_path: pathlib.Path,
) -> None:
    logdir = str(tmp_path / 'logs')
    configure_logging(logdir=logdir, level='INFO')
    # The directory is created eagerly so the file handler can write.
    assert pathlib.Path(logdir).is_dir()


def test_configure_logging_quiets_noisy_loggers() -> None:
    configure_logging(logdir=None, level='DEBUG')
    for name, level in _NOISY_LOGGERS.items():
        assert logging.getLogger(name).level == level


def test_log_timing_logs_duration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO), log_timing(logger, 'did %s', 'thing'):
        pass
    assert any(
        'did thing' in record.message and 'took' in record.message
        for record in caplog.records
    )


def test_log_timing_logs_on_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The duration should be logged even when the wrapped block raises so
    # slow failures remain visible.
    def _boom() -> None:
        msg = 'boom'
        raise ValueError(msg)

    with (
        caplog.at_level(logging.INFO),
        pytest.raises(ValueError, match='boom'),
        log_timing(logger, 'attempted %s', 'work'),
    ):
        _boom()
    assert any('attempted work' in record.message for record in caplog.records)


def test_log_timing_respects_level(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        caplog.at_level(logging.DEBUG),
        log_timing(logger, 'debug op', level=logging.DEBUG),
    ):
        pass
    records = [r for r in caplog.records if 'debug op' in r.message]
    assert len(records) == 1
    assert records[0].levelno == logging.DEBUG
