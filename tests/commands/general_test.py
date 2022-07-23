from __future__ import annotations

import pytest

from testing.mock import MockInteraction
from testing.mock import MockUser
from testing.utils import extract
from threepseat.commands.general import flip
from threepseat.commands.general import roll
from threepseat.commands.general import source


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


@pytest.mark.asyncio
async def test_source() -> None:
    source_ = extract(source)

    interaction = MockInteraction(roll, user='calling-user')

    await source_(interaction)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'github' in interaction.response_message
    )
