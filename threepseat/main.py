from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from collections.abc import Sequence
from typing import Any

import threepseat
from threepseat import config
from threepseat.bot import Bot
from threepseat.commands.custom import CustomCommands
from threepseat.logging import configure_logging
from threepseat.rules.commands import RulesCommands
from threepseat.sounds.commands import SoundCommands
from threepseat.sounds.data import Sounds
from threepseat.sounds.web import create_app


logger = logging.getLogger(__name__)


async def amain(cfg: config.Config, shutdown_event: asyncio.Event) -> None:
    """Run asyncio services."""
    custom_commands = CustomCommands(cfg.sqlite_database)
    rules_commands = RulesCommands(cfg.sqlite_database)
    sounds = Sounds(cfg.sqlite_database, cfg.sounds_path)
    sound_commands = SoundCommands(sounds)

    bot = Bot(
        playing_title=cfg.playing_title,
        custom_commands=custom_commands,
        rules_commands=rules_commands,
        sound_commands=sound_commands,
    )
    webapp = create_app(
        bot=bot,
        sounds=sounds,
        client_id=cfg.client_id,
        client_secret=cfg.client_secret,
        bot_token=cfg.bot_token,
        redirect_uri=cfg.redirect_uri,
    )

    await asyncio.gather(
        bot.start(cfg.bot_token, reconnect=True),
        webapp.run_task(
            host='0.0.0.0',
            port=cfg.sounds_port,
            certfile=cfg.sounds_certfile,
            keyfile=cfg.sounds_keyfile,
            # mypy disagrees but this is what the docs say to do
            # https://pgjones.gitlab.io/hypercorn/how_to_guides/api_usage.html?highlight=shutdown_trigger#graceful-shutdown  # noqa: E501
            shutdown_trigger=shutdown_event.wait,  # type: ignore
        ),
        return_exceptions=True,
    )


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

    shutdown_event = asyncio.Event()

    def _handler(_signo: int, _stack_frame: Any) -> None:  # pragma: no cover
        logger.warning('shutting down tasks...')
        shutdown_event.set()
        for task in asyncio.all_tasks():
            task.cancel()

    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)

    try:
        asyncio.run(amain(cfg, shutdown_event))
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info('done')
    except Exception as e:
        logger.exception(e)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
