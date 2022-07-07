from __future__ import annotations

import pathlib

from threepseat.utils import alphanumeric
from threepseat.utils import cached_load


def test_alphanumeric() -> None:
    assert alphanumeric('asdasdaASDASD213123')
    assert not alphanumeric(' ')
    assert not alphanumeric('$')


def test_cached_load(tmp_path: pathlib.Path) -> None:
    test_file = tmp_path / 'file.bytes'
    data = b'12345'
    with open(test_file, 'wb') as f:
        f.write(data)

    found = cached_load(test_file)
    assert found.getvalue() == data
