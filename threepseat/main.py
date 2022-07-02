from __future__ import annotations

import argparse
import sys
from typing import Sequence

import threepseat
from threepseat import config


def main(argv: Sequence[str] | None = None) -> int:
    """Main entrypoint for launching 3pseatBot."""
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog='threepseatbot')

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
        help='start bot using this config',
        metavar='PATH',
    )
    mutex_group.add_argument(
        '--template',
        help='create template config file',
        metavar='PATH',
    )

    if len(argv) == 0:
        argv = ['--help']

    args = parser.parse_args(argv)

    if args.template is not None:
        config.write_template(args.template)
        return 0

    cfg = config.load(args.config)

    # TODO:
    # - setup logging
    # - log cfg
    # - start amain()

    print(cfg)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
