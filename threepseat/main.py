from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from typing import Sequence

import threepseat
from threepseat import config
from threepseat.bot import Bot
from threepseat.logging import configure_logging


logger = logging.getLogger(__name__)


async def amain(cfg: config.Config) -> None:
    """Run asyncio services."""
    bot = Bot(cfg)
    await asyncio.gather(bot.start())


def main(argv: Sequence[str] | None = None) -> int:
    """Main entrypoint for launching 3pseatBot."""
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        description='3pseatBot CLI',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='python -m threepseatbot',
    )

    # https://stackoverflow.com/a/8521644/812183
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version=f'3pseatBot {threepseat.__version__}',
    )
    mutex_group = parser.add_mutually_exclusive_group(required=True)
    mutex_group.add_argument(
        '--config',
        metavar='PATH',
        help='start bot using this config',
    )
    mutex_group.add_argument(
        '--template',
        metavar='PATH',
        help='create template config file',
    )
    parser.add_argument(
        '--log-dir',
        metavar='PATH',
        help='optional directory to write logs to',
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING'],
        metavar='LEVEL',
        help='logging level',
    )

    if len(argv) == 0:
        argv = ['--help']

    args = parser.parse_args(argv)

    if args.template is not None:
        config.write_template(args.template)
        return 0

    configure_logging(logdir=args.log_dir, level=args.log_level)

    cfg = config.load(args.config)
    logger.info(cfg)

    try:
        asyncio.run(amain(cfg))
    except KeyboardInterrupt:
        logger.info('bot exited')
    except Exception as e:
        logger.exception(e)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
