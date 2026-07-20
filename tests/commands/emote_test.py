from __future__ import annotations

from unittest import mock

import discord
from emoji import emojize

from testing.asserts import assert_followed
from testing.mock import MockInteraction
from testing.utils import extract
from threepseat.commands.emote import emote


class _MockEmoji(discord.Emoji):
    def __init__(self, name: str) -> None:
        self._name = name

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:  # type: ignore[override]
        return self._name


async def test_emote() -> None:
    emote_ = extract(emote)

    interaction = MockInteraction(emote, user='calling-user', guild='myguild')

    emojis = [_MockEmoji('emote1'), _MockEmoji('emote2'), _MockEmoji('emote3')]

    with mock.patch.object(
        interaction.guild,
        'fetch_emojis',
        mock.AsyncMock(return_value=emojis),
    ):
        await emote_(interaction)

    message = assert_followed(interaction)
    assert 'emote' in message or emojize(':game_die:') in message


async def test_emote_no_emotes() -> None:
    emote_ = extract(emote)

    interaction = MockInteraction(emote, user='calling-user', guild='myguild')

    with mock.patch.object(
        interaction.guild,
        'fetch_emojis',
        mock.AsyncMock(return_value=[]),
    ):
        await emote_(interaction)

    assert_followed(interaction, 'no custom emotes')


async def test_emote_no_matches() -> None:
    emote_ = extract(emote)

    interaction = MockInteraction(emote, user='calling-user', guild='myguild')

    emojis = [_MockEmoji('emote1'), _MockEmoji('emote2'), _MockEmoji('emote3')]

    with mock.patch.object(
        interaction.guild,
        'fetch_emojis',
        mock.AsyncMock(return_value=emojis),
    ):
        await emote_(interaction, match='missing')

    assert_followed(interaction, 'No guild emotes match')
