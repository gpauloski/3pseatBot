from __future__ import annotations

from collections.abc import Generator

import pytest

from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.utils import extract
from threepseat.ext.games.commands import GamesCommands
from threepseat.ext.games.data import Game

GAME = Game(
    guild_id=1234,
    author_id=9012,
    creation_time=0,
    name='3pseat Simulator 2022',
)


@pytest.fixture
def games(tmp_file: str) -> Generator[GamesCommands, None, None]:
    yield GamesCommands(tmp_file)


@pytest.mark.asyncio
async def test_autocomplete(games) -> None:
    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(
        None,  # type: ignore
        user='user',
        guild=guild,
    )

    assert len(await games.autocomplete(interaction, current='')) == 0

    games.table.update(GAME._replace(name='A'))
    games.table.update(GAME._replace(name='B'))
    games.table.update(GAME._replace(guild_id=42))

    assert len(await games.autocomplete(interaction, current='')) == 2
    assert len(await games.autocomplete(interaction, current='A')) == 1


@pytest.mark.asyncio
async def test_add_game(games) -> None:
    add_ = extract(games.add)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.add, user='user', guild=guild)

    await add_(games, interaction, GAME.name)

    game = games.table.get(GAME.guild_id, GAME.name)
    assert game is not None

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'Added' in interaction.response_message


@pytest.mark.asyncio
async def test_add_game_exists(games) -> None:
    add_ = extract(games.add)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.add, user='user', guild=guild)

    games.table.update(GAME)
    await add_(games, interaction, GAME.name)

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'already exists' in interaction.response_message


@pytest.mark.asyncio
async def test_list_games(games) -> None:
    list_ = extract(games.list)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.list, user='user', guild=guild)

    games.table.update(GAME._replace(name='Game A'))
    games.table.update(GAME._replace(name='Game B'))
    games.table.update(GAME._replace(guild_id=42, name='Game C'))

    await list_(games, interaction)

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'Game A' in interaction.response_message
    assert 'Game B' in interaction.response_message
    assert 'Game C' not in interaction.response_message


@pytest.mark.asyncio
async def test_list_games_empty(games) -> None:
    list_ = extract(games.list)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.list, user='user', guild=guild)

    await list_(games, interaction)

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'No games' in interaction.response_message


@pytest.mark.asyncio
async def test_remove_game(games) -> None:
    remove_ = extract(games.remove)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.remove, user='user', guild=guild)

    games.table.update(GAME)

    await remove_(games, interaction, GAME.name)

    assert games.table.get(GAME.guild_id, GAME.name) is None
    assert interaction.responded
    assert interaction.response_message is not None
    assert 'Removed' in interaction.response_message


@pytest.mark.asyncio
async def test_remove_game_missing(games) -> None:
    remove_ = extract(games.remove)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.remove, user='user', guild=guild)

    await remove_(games, interaction, GAME.name)

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'does not exist' in interaction.response_message


@pytest.mark.asyncio
async def test_roll_games(games) -> None:
    roll_ = extract(games.roll)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.roll, user='user', guild=guild)

    games.table.update(GAME._replace(name='Game A'))
    games.table.update(GAME._replace(name='Game B'))
    games.table.update(GAME._replace(guild_id=42, name='Game C'))

    await roll_(games, interaction)

    assert interaction.responded
    assert interaction.response_message is not None
    assert (
        'Game A' in interaction.response_message
        or 'Game B' in interaction.response_message
    )
    assert 'Game C' not in interaction.response_message


@pytest.mark.asyncio
async def test_roll_games_empty(games) -> None:
    roll_ = extract(games.roll)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.roll, user='user', guild=guild)

    await roll_(games, interaction)

    assert interaction.responded
    assert interaction.response_message is not None
    assert 'No games' in interaction.response_message
