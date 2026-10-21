from __future__ import annotations

import datetime
from collections.abc import AsyncIterator
from collections.abc import Generator
from unittest import mock

import discord
import pytest
from emoji import emojize

from testing.mock import MockClient
from testing.mock import MockInteraction
from testing.mock import MockUser
from testing.utils import extract
from threepseat.commands.clan import clan

INVOKER = MockUser('invoker', 1)
BOT = MockUser('bot', 2, bot=True)
JUMP_URL = 'https://discord.com/channels/1/2/3'
NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


@pytest.fixture(autouse=True)
def mock_now() -> Generator[None, None, None]:
    with mock.patch('discord.utils.utcnow', return_value=NOW):
        yield


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
) -> tuple[MockInteraction, mock.AsyncMock, mock.AsyncMock]:
    # The cached original response never sees new reactions; only a fresh
    # fetch of the message does.
    fetched = mock.AsyncMock()
    fetched.reactions = list(reactions)
    message = mock.AsyncMock()
    message.reactions = []
    message.jump_url = JUMP_URL
    message.fetch.return_value = fetched
    interaction = MockInteraction(clan, user=INVOKER)
    interaction.original_response = mock.AsyncMock(  # type: ignore[method-assign]
        return_value=message,
    )
    interaction.edit_original_response = mock.AsyncMock()  # type: ignore[method-assign]
    return interaction, message, fetched


def _sent(fetched: mock.AsyncMock) -> str:
    fetched.channel.send.assert_awaited_once()
    return fetched.channel.send.await_args.args[0]  # type: ignore[no-any-return]


def _closed_at(minutes: int) -> str:
    end = NOW + datetime.timedelta(minutes=minutes)
    return discord.utils.format_dt(end, 'f')


async def test_clan_fewer_entrants_than_spots(
    mock_sleep: mock.AsyncMock,
) -> None:
    user = MockUser('user', 3)
    interaction, message, fetched = _interaction(_reaction(BOT, user))

    selected = await extract(clan)(interaction, 'Griffin', 3, 2)

    # Interaction tokens expire after 15 minutes so the interaction's
    # webhook must not be used after waiting.
    interaction.edit_original_response.assert_not_awaited()  # type: ignore[attr-defined]
    assert interaction.followup_message is None

    assert selected == [user]
    message.add_reaction.assert_awaited_once_with(
        emojize(':saluting_face:'),
    )
    message.remove_reaction.assert_awaited_once_with(
        emojize(':saluting_face:'),
        interaction.client.user,
    )
    mock_sleep.assert_awaited_once_with(120)
    assert interaction.response_message is not None
    assert 'Griffin' in interaction.response_message
    assert 'There are **3 spots available**.' in interaction.response_message
    assert 'Entries close <t:' in interaction.response_message
    assert ':R>. React to enter' in interaction.response_message
    assert _sent(fetched) == (
        '<@user> was selected for **Griffin** hosted by <@invoker>.'
    )


async def test_clan_more_entrants_than_spots() -> None:
    users = [MockUser(f'user{i}', 10 + i) for i in range(5)]
    interaction, _, fetched = _interaction(
        _reaction(*users[:3]),
        _reaction(*users[3:]),
    )

    selected = await extract(clan)(interaction, 'Devil', 2, 1)

    assert len(selected) == 2
    assert all(user in users for user in selected)
    sent = _sent(fetched)
    assert ' were selected for **Devil** hosted by <@invoker>.' in sent
    assert ' and ' in sent


async def test_clan_deduplicates_and_excludes_invoker() -> None:
    user = MockUser('user', 3)
    interaction, _, fetched = _interaction(
        _reaction(BOT, INVOKER, user),
        _reaction(user, INVOKER),
    )

    selected = await extract(clan)(interaction, 'Griffin', 1, 1)

    assert selected == [user]
    assert 'was selected for **Griffin**' in _sent(fetched)


async def test_clan_no_entrants() -> None:
    interaction, _, fetched = _interaction(_reaction(BOT, INVOKER))

    selected = await extract(clan)(interaction, 'Griffin', 2)

    assert selected == []
    assert _sent(fetched) == (
        'No one entered the drawing for **Griffin**, <@invoker>.'
    )
    fetched.edit.assert_awaited_once_with(
        content=(
            '<@invoker> is starting an event: **Griffin**'
            '\n\nThere were **2 spots available**. '
            f'Entries closed at {_closed_at(3)}. No one entered.'
        ),
    )


async def test_clan_event_header() -> None:
    interaction, _, _ = _interaction()

    await extract(clan)(interaction, 'Griffin 10x', 2)

    assert interaction.response_message is not None
    assert interaction.response_message.startswith(
        '<@invoker> is starting an event: **Griffin 10x**\n\n',
    )


async def test_clan_singular_wording() -> None:
    interaction, _, _ = _interaction()

    await extract(clan)(interaction, 'Griffin', 1, 1)

    assert interaction.response_message is not None
    assert 'There is **1 spot available**.' in interaction.response_message


async def test_clan_closes_entries_with_selected() -> None:
    users = [MockUser(f'user{i}', 10 + i) for i in range(3)]
    interaction, _, fetched = _interaction(_reaction(*users))

    await extract(clan)(interaction, 'Griffin 10x', 3)

    fetched.edit.assert_awaited_once_with(
        content=(
            '<@invoker> is starting an event: **Griffin 10x**'
            '\n\nThere were **3 spots available**. '
            f'Entries closed at {_closed_at(3)}. Selected: '
            '<@user0>, <@user1>, and <@user2>.'
        ),
    )


async def test_clan_skips_reaction_removal_without_client_user() -> None:
    interaction, message, _ = _interaction()
    interaction._client = MockClient(None)  # type: ignore[arg-type]

    await extract(clan)(interaction, 'Griffin', 2)

    message.remove_reaction.assert_not_awaited()
