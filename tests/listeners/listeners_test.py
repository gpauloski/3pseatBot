from __future__ import annotations

from threepseat.listeners.listeners import Listener
from threepseat.listeners.listeners import register_listener
from threepseat.listeners.listeners import registered_listeners


def test_listener_registration() -> None:
    async def _listener() -> None:  # pragma: no cover
        pass

    listener = Listener(_listener, event='on_message')

    assert listener not in registered_listeners()

    register_listener('on_message')(_listener)

    assert listener in registered_listeners()
