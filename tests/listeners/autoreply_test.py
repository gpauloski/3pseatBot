from __future__ import annotations

from unittest import mock

import pytest

from testing.mock import MockMessage
from testing.mock import MockUser
from threepseat.listeners.autoreply import buh_reply
from threepseat.listeners.autoreply import pog_reply


@pytest.mark.asyncio
async def test_buh_reply() -> None:
    # Test replies on match
    author = MockUser('name', 1234)
    message = MockMessage('buh')
    message.author = author
    author.bot = False
    with mock.patch.object(message, 'reply') as mocked_reply:
        await buh_reply(message)
        assert mocked_reply.await_count == 1

    # Test nothing on match
    message = MockMessage('pog')
    message.author = author
    with mock.patch.object(message, 'reply') as mocked_reply:
        await buh_reply(message)
        assert mocked_reply.await_count == 0

    # Test ignore bot messages
    message = MockMessage('buh')
    message.author = author
    author.bot = True
    with mock.patch.object(message, 'reply') as mocked_reply:
        await buh_reply(message)
        assert mocked_reply.await_count == 0


@pytest.mark.asyncio
async def test_pog_reply() -> None:
    # Test replies on match
    author = MockUser('name', 1234)
    message = MockMessage('pog')
    message.author = author
    author.bot = False
    with mock.patch.object(message, 'reply') as mocked_reply:
        await pog_reply(message)
        assert mocked_reply.await_count == 1

    # Test nothing on match
    message = MockMessage('buh')
    message.author = author
    with mock.patch.object(message, 'reply') as mocked_reply:
        await pog_reply(message)
        assert mocked_reply.await_count == 0

    # Test ignore bot messages
    message = MockMessage('pog')
    message.author = author
    author.bot = True
    with mock.patch.object(message, 'reply') as mocked_reply:
        await pog_reply(message)
        assert mocked_reply.await_count == 0
