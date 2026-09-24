from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Generator
from unittest import mock

import pytest
from emoji import emojize

from testing.mock import MockInteraction
from testing.mock import MockUser
from testing.utils import extract
from threepseat.commands.clan import clan

INVOKER = MockUser('invoker', 1)
BOT = MockUser('bot', 2, bot=True)


@pytest.fixture(autouse=True)
def mock_sleep() -> Generator[mock.AsyncMock, None, None]:
    with mock.patch(
        'threepseat.commands.clan.asyncio.sleep',
        new_callable=mock.AsyncMock,
    ) as mocked:
        yield mocked


def _reaction(*users: MockUser) -> mock.MagicMock:
    async def _users() -> AsyncIterator[MockUser]:
        for user in users:
            yield user

    reaction = mock.MagicMock()
    reaction.users = _users
    return reaction


def _interaction(
    *reactions: mock.MagicMock,
) -> tuple[MockInteraction, mock.AsyncMock]:
    # The cached original response never sees new reactions; only a fresh
    # fetch of the message does.
    fetched = mock.MagicMock()
    fetched.reactions = list(reactions)
    message = mock.AsyncMock()
    message.reactions = []
    message.fetch.return_value = fetched
    interaction = MockInteraction(clan, user=INVOKER)
    interaction.original_response = mock.AsyncMock(  # type: ignore[method-assign]
        return_value=message,
    )
    interaction.edit_original_response = mock.AsyncMock()  # type: ignore[method-assign]
    return interaction, message


async def test_clan_fewer_entrants_than_spots(
    mock_sleep: mock.AsyncMock,
) -> None:
    user = MockUser('user', 3)
    interaction, message = _interaction(_reaction(BOT, user))

    selected = await extract(clan)(interaction, 'Griffin', 2, 3)

    assert selected == [user]
    message.add_reaction.assert_awaited_once_with(
        emojize(':saluting_face:'),
    )
    mock_sleep.assert_awaited_once_with(120)
    assert interaction.response_message is not None
    assert 'Griffin' in interaction.response_message
    assert 'to join (3 spots available)' in interaction.response_message
    assert '\n>' not in interaction.response_message
    assert interaction.followup_message is not None
    assert '<@invoker>, <@user>' in interaction.followup_message
    assert 'randomly' not in interaction.followup_message


async def test_clan_more_entrants_than_spots() -> None:
    users = [MockUser(f'user{i}', 10 + i) for i in range(5)]
    interaction, _ = _interaction(_reaction(*users[:3]), _reaction(*users[3:]))

    selected = await extract(clan)(interaction, 'Devil', 1, 2)

    assert len(selected) == 2
    assert all(user in users for user in selected)
    assert interaction.followup_message is not None
    assert 'randomly picked 2 of 5)' in interaction.followup_message


async def test_clan_deduplicates_and_excludes_invoker() -> None:
    user = MockUser('user', 3)
    interaction, _ = _interaction(
        _reaction(BOT, INVOKER, user),
        _reaction(user, INVOKER),
    )

    selected = await extract(clan)(interaction, 'Griffin', 1, 1)

    assert selected == [user]
    assert interaction.followup_message is not None
    assert 'randomly' not in interaction.followup_message


async def test_clan_no_entrants() -> None:
    interaction, _ = _interaction(_reaction(BOT, INVOKER))

    selected = await extract(clan)(interaction, 'Griffin')

    assert selected == []
    assert interaction.followup_message is not None
    assert 'No one joined' in interaction.followup_message


async def test_clan_note() -> None:
    interaction, _ = _interaction()

    await extract(clan)(interaction, 'Griffin', 1, 2, 'running it 10x')

    assert interaction.response_message is not None
    assert interaction.response_message.endswith('\n> running it 10x')


async def test_clan_closes_signups() -> None:
    interaction, _ = _interaction()

    await extract(clan)(interaction, 'Griffin', 1, 2, 'running it 10x')

    interaction.edit_original_response.assert_awaited_once_with(  # type: ignore[attr-defined]
        content=(
            '<@invoker> is doing **Griffin**! Sign-ups are closed.'
            '\n> running it 10x'
        ),
    )
