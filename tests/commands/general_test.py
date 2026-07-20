from __future__ import annotations

from testing.asserts import assert_responded
from testing.mock import MockInteraction
from testing.mock import MockUser
from testing.utils import extract
from threepseat.commands.general import flip
from threepseat.commands.general import roll
from threepseat.commands.general import source


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
    assert_responded(interaction, 'reply-user')

    interaction = MockInteraction(flip, user='calling-user')

    res = await flip_(interaction)
    assert res in ('heads', 'tails')
    assert_responded(interaction, 'calling-user')


async def test_roll() -> None:
    roll_ = extract(roll)

    interaction = MockInteraction(roll, user='calling-user')
    user = MockUser('reply-user', 12345)
    start, end = 1, 5

    res = await roll_(interaction, start, end, user)
    assert start <= res <= end
    assert_responded(interaction, 'reply-user')

    interaction = MockInteraction(roll, user='calling-user')

    # roll should flip start and end to be consecutive
    res = await roll_(interaction, end, start)
    assert start <= res <= end
    assert_responded(interaction, 'calling-user')


async def test_source() -> None:
    source_ = extract(source)

    interaction = MockInteraction(source, user='calling-user')

    await source_(interaction)
    assert_responded(interaction, 'github')
