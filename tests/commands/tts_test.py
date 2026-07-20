from __future__ import annotations

from unittest import mock

from testing.asserts import assert_followed
from testing.asserts import assert_responded
from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.utils import extract
from threepseat.commands.tts import tts


async def test_tts_command() -> None:
    tts_ = extract(tts)

    guild = MockGuild('guild', 5678)
    interaction = MockInteraction(
        tts,
        user=MockMember('user', 1234, guild),
        guild=guild,
    )

    with (
        mock.patch('threepseat.commands.tts.voice_channel'),
        mock.patch('threepseat.commands.tts.play_sound'),
        mock.patch('threepseat.tts.gTTS'),
    ):
        await tts_(interaction, 'test message')

    assert_followed(interaction, 'Played')


async def test_tts_command_text_too_long() -> None:
    tts_ = extract(tts)

    guild = MockGuild('guild', 5678)
    interaction = MockInteraction(
        tts,
        user=MockMember('user', 1234, guild),
        guild=guild,
    )

    await tts_(interaction, 'x' * 201)

    assert_responded(interaction, 'Text length is limited')


async def test_tts_command_not_in_voice_channel() -> None:
    tts_ = extract(tts)

    guild = MockGuild('guild', 5678)
    interaction = MockInteraction(
        tts,
        user=MockMember('user', 1234, guild),
        guild=guild,
    )

    with mock.patch(
        'threepseat.commands.tts.voice_channel',
        return_value=None,
    ):
        await tts_(interaction, 'test message')

    assert_followed(interaction, 'must be in a voice channel')


async def test_tts_command_exception() -> None:
    tts_ = extract(tts)

    guild = MockGuild('guild', 5678)
    interaction = MockInteraction(
        tts,
        user=MockMember('user', 1234, guild),
        guild=guild,
    )

    with (
        mock.patch('threepseat.commands.tts.voice_channel'),
        mock.patch(
            'threepseat.commands.tts.play_sound',
            side_effect=Exception(),
        ),
        mock.patch('threepseat.tts.gTTS'),
    ):
        await tts_(interaction, 'test message')

    assert_followed(interaction, 'Failed to play TTS')
