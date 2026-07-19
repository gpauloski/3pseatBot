from __future__ import annotations

import contextlib
import datetime
import logging.handlers
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

# Third-party loggers that are noisy at INFO. We keep our own `threepseat`
# loggers at the CLI-selected level but quiet these to WARNING so the useful
# signal is not drowned out. The Quart/Hypercorn entries in particular remove
# the per-request route access logs.
_NOISY_LOGGERS: dict[str, int] = {
    'hypercorn.access': logging.WARNING,
    'hypercorn.error': logging.WARNING,
    'quart.app': logging.WARNING,
    'quart.serving': logging.WARNING,
    'discord': logging.WARNING,
    'quart_discord': logging.WARNING,
    'urllib3': logging.WARNING,
}


def configure_logging(
    logdir: str | None,
    level: Literal['DEBUG', 'INFO', 'WARNING'],
) -> None:
    """Configure logging level, formats, and handlers."""
    stream_handler: logging.Handler = logging.StreamHandler(sys.stdout)
    file_handler: logging.Handler | None = None

    handlers: list[logging.Handler] = [stream_handler]
    if logdir is not None:
        Path(logdir).mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            Path(logdir) / 'bot.log',
            # Rotate logs Sunday at midnight
            when='W6',
            atTime=datetime.time(hour=0, minute=0, second=0),
        )
        handlers.append(file_handler)

    fmt = '[%(asctime)s.%(msecs)03d] %(levelname)s (%(name)s): %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    # Emit timestamps in the system's local time. This is Python's default, but
    # we set it explicitly so log times track the host/container wall clock
    # (see the Docker TZ configuration) and are not silently switched to UTC.
    logging.Formatter.converter = time.localtime

    logging.basicConfig(
        format=fmt,
        datefmt=datefmt,
        level=level,
        handlers=handlers,
    )

    for name, logger_level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(logger_level)

    logging.captureWarnings(True)


@contextlib.contextmanager
def log_timing(
    logger: logging.Logger,
    message: str,
    *args: object,
    level: int = logging.INFO,
) -> Iterator[None]:
    """Log the wall-clock duration of the wrapped block.

    Logs ``message`` (with ``args`` interpolated lazily, as with the standard
    logging methods) once the block exits, appending how long it took. The
    duration is logged even if the block raises so slow failures are visible.

    Usage:
        >>> with log_timing(logger, 'downloaded %s', link):
        >>>     download(link)

    Args:
        logger (logging.Logger): logger to emit the record on so that the log's
            module name stays accurate.
        message (str): log message, may contain %-style placeholders for args.
        args (object): arguments interpolated into message.
        level (int): logging level to emit at (default: INFO).
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        # Append the timing placeholder to the caller's message so the
        # duration is %-formatted lazily alongside their own args.
        fmt = message + ' (took %.2fs)'
        logger.log(level, fmt, *args, elapsed)
