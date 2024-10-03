from __future__ import annotations

import datetime
import logging.handlers
import os
import sys
from typing import Literal


def configure_logging(
    logdir: str | None,
    level: Literal['DEBUG', 'INFO'],
) -> None:
    """Configure logging level, formats, and handlers."""
    stream_handler: logging.Handler = logging.StreamHandler(sys.stdout)
    file_handler: logging.Handler | None = None

    handlers: list[logging.Handler] = [stream_handler]
    if logdir is not None:
        os.makedirs(logdir, exist_ok=True)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            os.path.join(logdir, 'bot.log'),
            # Rotate logs Sunday at midnight
            when='W6',
            atTime=datetime.time(hour=0, minute=0, second=0),
        )
        handlers.append(file_handler)

    fmt = '[%(asctime)s.%(msecs)03d] %(levelname)s (%(name)s): %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    logging.basicConfig(
        format=fmt,
        datefmt=datefmt,
        level=level,
        handlers=handlers,
    )

    logging.captureWarnings(True)

    # discord.utils.setup_logging(
    #     handler=stream_handler if file_handler is None else file_handler,
    #     formatter=logging.Formatter(fmt, datefmt),
    #     level=logging.getLevelName(level),
    #     root=False,
    # )
