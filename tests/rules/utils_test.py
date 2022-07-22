from __future__ import annotations

from unittest import mock

import discord

from testing.mock import MockGuild
from testing.mock import MockMember
from testing.mock import MockUser
from threepseat.rules.utils import ignore_message
from threepseat.rules.utils import is_booster
from threepseat.rules.utils import is_emoji
from threepseat.rules.utils import is_url


def test_is_booster() -> None:
    with mock.patch(
        'discord.Guild.premium_subscriber_role',
        new_callable=mock.PropertyMock(return_value='premium'),
    ):
        guild = MockGuild('guild', 5678)
        with mock.patch(
            'discord.Member.roles',
            new_callable=mock.PropertyMock(return_value=[]),
        ):
            member = MockMember('user', 1234, guild)
            assert not is_booster(member)

        with mock.patch(
            'discord.Member.roles',
            new_callable=mock.PropertyMock(return_value=['premium']),
        ):
            member = MockMember('user', 1234, guild)
            assert is_booster(member)


def test_is_emoji() -> None:
    assert not is_emoji('')
    assert not is_emoji('     ')
    assert is_emoji('\U0001F600')
    assert is_emoji('\U0001F600 \U0001F600 \U0001F600')
    assert is_emoji('<:pog:>')
    assert is_emoji('<:pog:1> \U0001F600')
    assert not is_emoji('<::>')
    assert is_emoji('<:pog:123123231233>')
    assert is_emoji('<a:pog:123123231233>')


def test_is_url() -> None:
    assert not is_url('')
    assert not is_url('https://google .com')
    assert is_url('https://google.com')
    assert is_url('www.google.com')
    assert is_url('http://google.com')
    assert is_url('google.com')
    assert is_url('https://google.com/route')
    assert is_url('https://google.com/search?query=3pseatbot')


@mock.patch('discord.Message')
def test_ignore_message_successes(mock_message) -> None:
    # Ignore non-default type messages
    message = discord.Message()  # type: ignore
    message.type = discord.MessageType.pins_add
    assert ignore_message(message)

    # Ignore bots
    message = discord.Message()  # type: ignore
    message.type = discord.MessageType.default
    message.author = MockUser('user', 1234)
    message.author.bot = True
    assert ignore_message(message)

    # Ignore server boosters
    message.author.bot = False
    with (
        mock.patch('threepseat.rules.utils.is_booster', return_value=True),
        mock.patch('threepseat.rules.utils.isinstance', return_value=True),
    ):
        assert ignore_message(message)

    # Ignore emojis
    message.content = '<:pog:1234>'
    assert ignore_message(message)

    # Ignore urls
    message.content = 'google.com'
    assert ignore_message(message)

    # Ignore just attachments
    message.content = '  '
    message.attachments = ['attachment']  # type: ignore
    assert ignore_message(message)

    # Ignore starts with quote
    message.content = '> quoted'
    assert ignore_message(message)

    # Ignore code block
    message.content = '```code```'
    assert ignore_message(message)


@mock.patch('discord.Message')
def test_ignore_message_failures(mock_message) -> None:
    with (
        mock.patch('threepseat.rules.utils.is_booster', return_value=False),
    ):
        message = discord.Message()  # type: ignore
        message.type = discord.MessageType.default
        message.author = MockUser('user', 1234)
        message.author.bot = False
        message.content = 'normal text'
        assert not ignore_message(message)
