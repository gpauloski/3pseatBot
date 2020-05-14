import logging
import time
import os
import sys
import argparse
import contextlib

import bot

def parse_args():
    parser = argparse.ArgumentParser(description="3pseatBot. A bot that does"
                                                 " little of use.")
    parser.add_argument("--logdir", default="logs", 
                        help="Logging directory (Default='logs')")
    parser.add_argument("--config", default="config.cfg", 
                        help="Bot config file (Default='config.cfg'")

    args = parser.parse_args()
    return args


@contextlib.contextmanager
def init_logger(log_dir=None, filename=None):
    try: 
        if filename is None:
            filename = time.strftime("%Y-%m-%d_%H-%M-%S") + "_bot.log"
        if log_dir is not None:
            os.makedirs(log_dir, exist_ok=True)
            filename = os.path.join(log_dir, filename)
 
        logger = logging.getLogger()

        stream_handler = logging.StreamHandler(sys.stdout)
        format_str = "%(asctime)s.%(msecs)03d [%(levelname)-7.7s]  %(message)s"
        format_date = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(format_str, format_date)
        stream_handler.setFormatter(formatter)
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

        yield
    finally:
        for handle in logger.handlers:
            handle.close()
            logger.removeHandler(handle)


def launch_bot(config):
    threepseatbot = bot.Bot(config)
    threepseatbot.run()


def main():
    args = parse_args()
    with init_logger(log_dir=args.logdir):
        launch_bot(args.config)


if __name__ == '__main__':
    main()

