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
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if logdir is not None:
        os.makedirs(logdir, exist_ok=True)
        handlers.append(
            logging.handlers.TimedRotatingFileHandler(
                os.path.join(logdir, 'bot.log'),
                # Rotate logs Sunday at midnight
                when='W6',
                atTime=datetime.time(hour=0, minute=0, second=0),
            ),
        )

    logging.basicConfig(
        format=(
            '[%(asctime)s.%(msecs)03d] %(levelname)s (%(name)s): '
            '%(message)s'
        ),
        datefmt='%Y-%m-%d %H:%M:%S',
        level=level,
        handlers=handlers,
    )
