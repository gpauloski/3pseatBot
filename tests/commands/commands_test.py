from __future__ import annotations

from threepseat.commands.commands import registered_commands


def test_commands_registered() -> None:
    assert len(registered_commands()) > 0
