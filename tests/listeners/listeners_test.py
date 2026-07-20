from __future__ import annotations

from threepseat.listeners import LISTENERS


def test_listeners_declared() -> None:
    assert len(LISTENERS) > 0
    for listener in LISTENERS:
        assert callable(listener.func)
        assert listener.event.startswith('on_')
