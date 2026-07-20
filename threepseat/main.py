from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from collections.abc import Sequence
from types import FrameType

from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig

import threepseat
from threepseat import config
from threepseat.bot import Bot
from threepseat.ext.birthdays import BirthdayCommands
from threepseat.ext.custom import CustomCommands
from threepseat.ext.games import GamesCommands
from threepseat.ext.reminders import ReminderCommands
from threepseat.ext.rules import RulesCommands
from threepseat.ext.sounds import SoundCommands
from threepseat.ext.sounds.web import create_app
from threepseat.logging import configure_logging

logger = logging.getLogger(__name__)


def webapp_config(cfg: config.Config) -> HypercornConfig:
    """Build the hypercorn config used to serve the sounds web app.

    Quart's `run_task()` hardcodes `accesslog = '-'`, which makes hypercorn
    install its own stdout handlers with its own format and reset the
    `hypercorn.*` log levels to INFO, overriding `configure_logging()`. Handing
    it `Logger` instances instead leaves those loggers alone, so hypercorn's
    output uses our format and respects the levels in `threepseat.logging`.
    """
    hypercorn_config = HypercornConfig()
    hypercorn_config.access_log_format = '%(h)s %(r)s %(s)s %(b)s %(D)s'
    hypercorn_config.accesslog = logging.getLogger('hypercorn.access')
    hypercorn_config.errorlog = logging.getLogger('hypercorn.error')
    # Bind to all interfaces since this runs in a container and needs to be
    # reachable via the host's port mapping.
    hypercorn_config.bind = [f'0.0.0.0:{cfg.sounds_port}']
    hypercorn_config.certfile = cfg.sounds_certfile
    hypercorn_config.keyfile = cfg.sounds_keyfile
    return hypercorn_config


async def amain(cfg: config.Config, shutdown_event: asyncio.Event) -> None:
    """Run asyncio services."""
    birthday_commands = BirthdayCommands(cfg.sqlite_database)
    custom_commands = CustomCommands(cfg.sqlite_database)
    games_commands = GamesCommands(cfg.sqlite_database)
    reminder_commands = ReminderCommands(cfg.sqlite_database)
    rules_commands = RulesCommands(cfg.sqlite_database)
    sound_commands = SoundCommands(cfg.sqlite_database, cfg.sounds_path)
    sounds = sound_commands.table
    member_sounds = sound_commands.join_table

    bot = Bot(
        playing_title=cfg.playing_title,
        extensions=[
            birthday_commands,
            custom_commands,
            games_commands,
            reminder_commands,
            rules_commands,
            sound_commands,
        ],
    )

    webapp = create_app(
        bot=bot,
        sounds=sounds,
        member_sounds=member_sounds,
        client_id=cfg.client_id,
        client_secret=cfg.client_secret,
        bot_token=cfg.bot_token,
        redirect_uri=cfg.redirect_uri,
        secret_key=cfg.secret_key,
    )

    async def wait_for_shutdown() -> None:
        # hypercorn's shutdown_trigger expects Awaitable[None], but
        # asyncio.Event.wait() resolves to True, hence this wrapper.
        await shutdown_event.wait()

    services = ('bot', 'webapp')
    async with bot:
        results = await asyncio.gather(
            bot.start(cfg.bot_token, reconnect=True),
            serve(
                webapp,
                webapp_config(cfg),
                shutdown_trigger=wait_for_shutdown,
            ),
            return_exceptions=True,
        )

    # gather(return_exceptions=True) prevents one service crashing from tearing
    # down the other, but it also swallows the exceptions. Surface any real
    # failures (a CancelledError is the expected result of a clean shutdown) so
    # they are logged and main() exits non-zero rather than silently.
    first_error: BaseException | None = None
    for service, result in zip(services, results, strict=True):
        if isinstance(result, asyncio.CancelledError):
            continue
        if isinstance(result, BaseException):
            logger.error('%s exited with an error', service, exc_info=result)
            if first_error is None:
                first_error = result
    if first_error is not None:
        raise first_error


def main(argv: Sequence[str] | None = None) -> int:
    """Main entrypoint for launching 3pseatBot."""
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        description='3pseatBot CLI',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        # Matches the console script in pyproject.toml; "python -m threepseat"
        # also works but the installed entrypoint is what users are told about.
        prog='threepseatbot',
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

    def _handler(  # pragma: no cover
        _signo: int,
        _stack_frame: FrameType | None,
    ) -> None:
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
    except Exception:
        logger.exception('unhandled exception')
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
