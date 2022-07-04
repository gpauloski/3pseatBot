from __future__ import annotations

from typing import Any
from typing import Awaitable
from typing import Callable

import pytest

from testing.mock import MockInteraction
from testing.mock import MockUser
from threepseat.commands import flip
from threepseat.commands import registered_commands
from threepseat.commands import roll


def extract(app_command) -> Callable[..., Awaitable[Any]]:
    """Extract the original function from the Command."""
    return app_command._callback


def test_commands_registered() -> None:
    assert len(registered_commands()) > 0


@pytest.mark.asyncio
async def test_flip() -> None:
    flip_ = extract(flip)

    interaction = MockInteraction(
        flip,
        user='calling-user',
        message='message',
        channel='mychannel',
        guild='myguild',
    )
    user = MockUser('reply-user', 12345)

    res = await flip_(interaction, user)
    assert res in ('heads', 'tails')
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'reply-user' in interaction.response_message
    )

    interaction = MockInteraction(flip, user='calling-user')

    res = await flip_(interaction)
    assert res in ('heads', 'tails')
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'calling-user' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_roll() -> None:
    roll_ = extract(roll)

    interaction = MockInteraction(roll, user='calling-user')
    user = MockUser('reply-user', 12345)
    start, end = 1, 5

    res = await roll_(interaction, start, end, user)
    assert start <= res <= end
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'reply-user' in interaction.response_message
    )

    interaction = MockInteraction(roll, user='calling-user')

    # roll should flip start and end to be consecutive
    res = await roll_(interaction, end, start)
    assert start <= res <= end
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'calling-user' in interaction.response_message
    )
