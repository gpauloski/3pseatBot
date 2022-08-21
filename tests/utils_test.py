from __future__ import annotations

import asyncio
import pathlib
from unittest import mock

import discord
import pytest

from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockMember
from testing.mock import MockUser
from testing.mock import MockVoiceChannel
from threepseat.bot import Bot
from threepseat.utils import alphanumeric
from threepseat.utils import cached_load
from threepseat.utils import leave_on_empty
from threepseat.utils import play_sound
from threepseat.utils import primary_channel
from threepseat.utils import readable_sequence
from threepseat.utils import readable_timedelta
from threepseat.utils import split_strings
from threepseat.utils import voice_channel


def test_alphanumeric() -> None:
    assert alphanumeric('asdasdaASDASD213123')
    assert not alphanumeric(' ')
    assert not alphanumeric('$')


def test_cached_load(tmp_path: pathlib.Path) -> None:
    test_file = tmp_path / 'file.bytes'
    data = b'12345'
    with open(test_file, 'wb') as f:
        f.write(data)

    found = cached_load(test_file)
    assert found.getvalue() == data


def test_split_strings() -> None:
    assert split_strings('') == []
    assert split_strings('     ') == []
    assert split_strings('abc') == ['abc']
    assert split_strings(' abc, def ') == ['abc', 'def']
    assert split_strings('axbxcx', delimiter='x') == ['a', 'b', 'c']


def test_primary_channel() -> None:
    guild = MockGuild('myguild', 5678)
    with mock.patch('discord.TextChannel'):
        channel = discord.TextChannel()  # type: ignore
    with mock.patch(
        'discord.Guild.system_channel',
        mock.PropertyMock(return_value=channel),
    ):
        assert primary_channel(guild) == channel

    with (
        mock.patch(
            'discord.Guild.system_channel',
            mock.PropertyMock(return_value=None),
        ),
        mock.patch(
            'discord.Guild.me',
            mock.PropertyMock(),
        ),
    ):
        guild._channels = {}
        assert primary_channel(guild) is None

        guild._channels = {'c1': channel}  # type: ignore
        with mock.patch('threepseat.utils.isinstance', return_value=True):
            assert primary_channel(guild) == channel

        with mock.patch('discord.VoiceChannel'):
            channel = discord.VoiceChannel()  # type: ignore
        guild._channels = {'c1': channel}  # type: ignore
        with mock.patch('threepseat.utils.isinstance', return_value=False):
            assert primary_channel(guild) is None


@pytest.mark.parametrize(
    'values,conjunction,expected',
    (
        ([], 'and', ''),
        (['a'], 'and', 'a'),
        (['a', 'b'], 'and', 'a and b'),
        (['a', 'b', 'c', 'd'], 'or', 'a, b, c, or d'),
    ),
)
def test_readable_sequence(
    values: list[str],
    conjunction: str,
    expected: str,
) -> None:
    assert readable_sequence(values, conjunction) == expected


@pytest.mark.parametrize(
    'args,expected',
    (
        # Default value
        ({}, '0 seconds'),
        # Singular vs plural
        ({'days': 1}, '1 day'),
        ({'days': 2}, '2 days'),
        ({'hours': 1}, '1 hour'),
        ({'hours': 2}, '2 hours'),
        ({'minutes': 1}, '1 minute'),
        ({'minutes': 2}, '2 minutes'),
        ({'seconds': 1}, '1 second'),
        ({'seconds': 2}, '2 seconds'),
        # Two non-zero items (concatenates with and)
        ({'minutes': 3, 'seconds': 1}, '3 minutes and 1 second'),
        # Three or more non-zero items (concatenates with commas and and)
        (
            {'days': 5, 'minutes': 3, 'seconds': 1},
            '5 days, 3 minutes, and 1 second',
        ),
        (
            {'days': 5, 'hours': 25, 'minutes': 3, 'seconds': 1},
            '6 days, 1 hour, 3 minutes, and 1 second',
        ),
        # Negative values
        ({'minutes': 3, 'seconds': -1}, '2 minutes and 59 seconds'),
        ({'days': -3, 'minutes': -1}, '-4 days, 23 hours, and 59 minutes'),
    ),
)
def test_readable_timedelta(args: dict[str, float], expected: str) -> None:
    assert readable_timedelta(**args) == expected


def test_voice_channel() -> None:
    member = MockMember('username', 1234, MockGuild('myguild', 5678))

    assert voice_channel(member) is None

    class Voice1:
        channel = MockVoiceChannel()

    member._voice = Voice1()  # type: ignore
    assert member.voice is not None
    assert voice_channel(member) == member.voice.channel

    class Voice2:
        channel = object()

    member._voice = Voice2()  # type: ignore
    assert voice_channel(member) is None


@pytest.mark.asyncio
@mock.patch('discord.FFmpegPCMAudio')
async def test_play_sound(mock_audio) -> None:
    sound = 'filepath'
    channel = MockVoiceChannel()

    client = MockClient(MockUser('name', 1234))
    voice_client = discord.VoiceProtocol(client=client, channel=channel)
    voice_client.move_to = mock.AsyncMock()  # type: ignore
    voice_client.play = mock.AsyncMock()  # type: ignore

    # Note: first True to see if there is a current sound to be stopped,
    # then True to allow wait to happen, then False to exit wait loop
    voice_client.is_playing = mock.MagicMock(  # type: ignore
        side_effect=[True, True, False],
    )
    voice_client.stop = mock.MagicMock()  # type: ignore

    with (
        mock.patch.object(channel, 'guild', mock.PropertyMock()),
        mock.patch.object(
            channel.guild,
            'voice_client',
            new_callable=mock.PropertyMock(return_value=voice_client),
        ),
    ):
        await play_sound(sound, channel, wait=True)

    voice_client.is_playing = mock.MagicMock(  # type: ignore
        return_value=False,
    )

    with (
        mock.patch.object(
            channel,
            'connect',
            mock.AsyncMock(return_value=voice_client),
        ),
        mock.patch.object(channel, 'guild', mock.PropertyMock()),
        mock.patch.object(
            channel.guild,
            'voice_client',
            new_callable=mock.PropertyMock(return_value=None),
        ),
    ):
        await play_sound(sound, channel)


@pytest.mark.asyncio
async def test_leave_on_empty() -> None:
    class MockVoiceClient(discord.VoiceClient):
        def __init__(self) -> None:
            self.channel = MockVoiceChannel()

    class MockVoiceProtocol(discord.VoiceProtocol):
        def __init__(self) -> None:
            pass

    mock1 = MockVoiceClient()
    mock2 = MockVoiceProtocol()
    with (
        mock.patch(
            'threepseat.bot.Bot.voice_clients',
            new_callable=mock.PropertyMock(return_value=[mock1, mock2]),
        ),
        mock.patch.object(mock1, 'disconnect', mock.AsyncMock()) as disconnect,
    ):
        bot = Bot()
        task = leave_on_empty(bot, 0.01)
        task.start()
        await asyncio.sleep(0.03)
        assert task.is_running()
        assert task.current_loop > 0
        task.stop()
        assert disconnect.await_count > 0
