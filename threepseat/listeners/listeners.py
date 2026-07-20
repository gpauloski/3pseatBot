from __future__ import annotations

from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any
from typing import NamedTuple

type CoroFunc = Callable[..., Coroutine[Any, Any, Any]]


class Listener(NamedTuple):
    """Listener function and the event it handles."""

    func: CoroFunc
    event: str
