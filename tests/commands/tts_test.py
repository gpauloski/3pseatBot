from __future__ import annotations

from unittest import mock

import pytest

from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.utils import extract
from threepseat.commands.tts import tts


@pytest.mark.asyncio
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

    assert interaction.followed
    assert interaction.followup_message is not None and (
        'Played' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_tts_command_text_too_long() -> None:
    tts_ = extract(tts)

    guild = MockGuild('guild', 5678)
    interaction = MockInteraction(
        tts,
        user=MockMember('user', 1234, guild),
        guild=guild,
    )

    await tts_(interaction, 'x' * 201)

    assert interaction.responded
    assert interaction.response_message is not None and (
        'Text length is limited' in interaction.response_message
    )


@pytest.mark.asyncio
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

    assert interaction.followed
    assert interaction.followup_message is not None and (
        'must be in a voice channel' in interaction.followup_message
    )


@pytest.mark.asyncio
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

    assert interaction.followed
    assert interaction.followup_message is not None and (
        'Failed to play TTS' in interaction.followup_message
    )
