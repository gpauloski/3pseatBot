from __future__ import annotations

import pytest

from threepseat.typing import base_type
from threepseat.typing import is_optional
from threepseat.typing import split_types


def test_base_type() -> None:
    assert base_type(int | None) is int
    assert base_type(str | None) is str

    with pytest.raises(ValueError):
        assert base_type(int)

    with pytest.raises(ValueError):
        assert base_type(None)  # type: ignore

    with pytest.raises(ValueError):
        assert base_type(int | float)


def test_is_optional() -> None:
    assert is_optional(int | None)
    assert is_optional(None | float)
    assert is_optional(int | float | None)

    assert not is_optional(type(None))
    assert not is_optional(int)
    assert not is_optional(float)


def test_split_types() -> None:
    assert split_types(int) == (int,)
    assert split_types(int | float) == (int, float)
    assert split_types(int | float | None) == (int, float, type(None))
