from __future__ import annotations

from collections.abc import Awaitable
from collections.abc import Callable
from unittest import mock

import discord
import pytest

from testing.mock import MockMessage
from testing.mock import MockUser
from threepseat.listeners.autoreply import buh_reply
from threepseat.listeners.autoreply import pog_reply

Reply = Callable[[discord.Message], Awaitable[None]]


@pytest.mark.parametrize(
    ('reply', 'content', 'bot', 'expected_replies'),
    [
        (buh_reply, 'buh', False, 1),
        # No reply when the message does not match the trigger.
        (buh_reply, 'pog', False, 0),
        # No reply to other bots, even on a match.
        (buh_reply, 'buh', True, 0),
        (pog_reply, 'pog', False, 1),
        (pog_reply, 'buh', False, 0),
        (pog_reply, 'pog', True, 0),
    ],
)
async def test_autoreply(
    reply: Reply,
    content: str,
    bot: bool,
    expected_replies: int,
) -> None:
    author = MockUser('name', 1234)
    author.bot = bot
    message = MockMessage(content)
    message.author = author

    with mock.patch.object(message, 'reply') as mocked_reply:
        await reply(message)

    assert mocked_reply.await_count == expected_replies
