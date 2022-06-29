from __future__ import annotations

import argparse
import sys
from typing import Sequence

import threepseat


def main(argv: Sequence[str] | None = None) -> int:
    """Main entrypoint for launching 3pseatBot."""
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(prog='threepseatbot')

    # https://stackoverflow.com/a/8521644/812183
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version=f'%(prog)s {threepseat.__version__}',
    )

    parser.parse_args(argv)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
