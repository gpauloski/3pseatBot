from __future__ import annotations

from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any
from typing import NamedTuple
from typing import TypeVar

_listeners: list[Listener] = []

T = TypeVar('T')
Coro = Coroutine[Any, Any, T]
CoroFunc = Callable[..., Coro[Any]]


class Listener(NamedTuple):
    """Listener function and event."""

    func: CoroFunc
    event: str


def register_listener(event: str) -> Callable[[CoroFunc], CoroFunc]:
    """Decorator to register listener.

    Usage:
        >>> @register_listener('on_message')
        >>> def message_handler(...) -> None: ...
    """

    def _decorator(func: CoroFunc) -> CoroFunc:
        _listeners.append(Listener(func, event))
        return func

    return _decorator


def registered_listeners() -> list[Listener]:
    """Get list of registered listeners."""
    # Shallow copy here so caller does not mess up our list
    return _listeners[:]
