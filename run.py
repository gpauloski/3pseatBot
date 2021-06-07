"""Runner script for 3pseatBot"""
# Monkey patch threading for WSGIServer
from gevent import monkey

monkey.patch_all()

import argparse
import json
import logging
import time
import os
import requests
import sys
import threading

from dotenv import load_dotenv
from gevent.pywsgi import WSGIServer
from typing import Optional

from threepseat.bot import Bot
from threepseat.soundboard.service import get_app


IFTTT_REQUEST = 'https://maker.ifttt.com/trigger/{trigger}/with/key/{key}'


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='3pseatBot. A bot that does little of use.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--config', required=True, help='Bot config file')
    parser.add_argument('--log_dir', default='logs', help='Logging directory')

    args = parser.parse_args()
    return args


def init_logger(
    log_dir: Optional[str] = None, filename: Optional[str] = None
) -> logging.Logger:
    """Logging Context Manager

    Logs to stdout and persistent file.

    Usage:
        >>> with init_logger():
        >>>     ...

    Args:
        log_dir (str): optional path to directory to write log files to
        filename (str): optional filename for log file
    """
    if filename is None:
        filename = time.strftime("%Y-%m-%d_%H-%M-%S") + '_bot.log'
    if log_dir is not None:
        os.makedirs(log_dir, exist_ok=True)
        filename = os.path.join(log_dir, filename)

    logger = logging.getLogger()

    # Disable default handlers
    if logger.handlers:
        logger.handlers = []

    stream_handler = logging.StreamHandler(sys.stdout)
    format_str = '%(asctime)s.%(msecs)03d [%(levelname)-7.7s]  %(message)s'
    format_date = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(format_str, format_date)
    stream_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    def exception_handler(type, value, tb):
        logger.exception('Uncaught exception: {}'.format(str(value)))

    sys.excepthook = exception_handler

    return logger


def main():
    """Initialize and run bot"""
    args = parse_args()

    init_logger(log_dir=args.log_dir)

    with open(args.config) as f:
        config = json.load(f)

    load_dotenv(dotenv_path='.env')

    discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
    ifttt_trigger = os.getenv('IFTTT_TRIGGER', None)
    ifttt_key = os.getenv('IFTTT_KEY', None)

    soundboard_config = config.pop('soundboard')
    discord_client_id = os.getenv('DISCORD_CLIENT_ID', None)
    discord_client_secret = os.getenv('DISCORD_CLIENT_SECRET', None)

    try:
        threepseatbot = Bot(token=discord_bot_token, **config)

        # Start REST app in separate thread if we have necessary information
        if discord_client_secret is not None and discord_bot_token is not None:
            app = get_app(
                threepseatbot,
                soundboard_config['redirect'],
                soundboard_config['port'],
                discord_client_id,
                discord_client_secret,
                discord_bot_token,
                static_site=soundboard_config['static'],
            )
            ssl_cert = soundboard_config['ssl_cert']
            ssl_key = soundboard_config['ssl_key']
            http_server = WSGIServer(
                ('', soundboard_config['port']), 
                app,
                keyfile=ssl_key,
                certfile=ssl_cert
            )
            threading.Thread(target=http_server.serve_forever).start()

        threepseatbot.run()
    except Exception as e:
        if ifttt_trigger is not None and ifttt_key is not None:
            requests.post(
                IFTTT_REQUEST.format(trigger=ifttt_trigger, key=ifttt_key),
                data={'value1': str(e)},
            )
        raise e


if __name__ == '__main__':
    main()
