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

    voice_client.is_playing = mock.MagicMock(return_value=True)  # type: ignore
    voice_client.stop = mock.MagicMock()  # type: ignore

    with (
        mock.patch.object(channel, 'guild', mock.PropertyMock()),
        mock.patch.object(
            channel.guild,
            'voice_client',
            new_callable=mock.PropertyMock(return_value=voice_client),
        ),
    ):
        await play_sound(sound, channel)

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
