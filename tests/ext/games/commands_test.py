from __future__ import annotations

import pytest

from testing.asserts import assert_responded
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
def games(tmp_file: str) -> GamesCommands:
    return GamesCommands(tmp_file)


async def test_autocomplete(games: GamesCommands) -> None:
    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(
        None,  # type: ignore[arg-type]
        user='user',
        guild=guild,
    )

    assert len(await games.autocomplete(interaction, current='')) == 0

    games.table.update(GAME._replace(name='A'))
    games.table.update(GAME._replace(name='B'))
    games.table.update(GAME._replace(guild_id=42))

    assert len(await games.autocomplete(interaction, current='')) == 2
    assert len(await games.autocomplete(interaction, current='A')) == 1


async def test_add_game(games: GamesCommands) -> None:
    add_ = extract(games.add)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.add, user='user', guild=guild)

    await add_(games, interaction, GAME.name)

    game = games.table.get(GAME.guild_id, GAME.name)
    assert game is not None

    assert_responded(interaction, 'Added')


async def test_add_game_exists(games: GamesCommands) -> None:
    add_ = extract(games.add)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.add, user='user', guild=guild)

    games.table.update(GAME)
    await add_(games, interaction, GAME.name)

    assert_responded(interaction, 'already exists')


async def test_list_games(games: GamesCommands) -> None:
    list_ = extract(games.list)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.list, user='user', guild=guild)

    games.table.update(GAME._replace(name='Game A'))
    games.table.update(GAME._replace(name='Game B'))
    games.table.update(GAME._replace(guild_id=42, name='Game C'))

    await list_(games, interaction)

    message = assert_responded(interaction, 'Game A')
    assert 'Game B' in message
    assert 'Game C' not in message


async def test_list_games_empty(games: GamesCommands) -> None:
    list_ = extract(games.list)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.list, user='user', guild=guild)

    await list_(games, interaction)

    assert_responded(interaction, 'No games')


async def test_remove_game(games: GamesCommands) -> None:
    remove_ = extract(games.remove)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.remove, user='user', guild=guild)

    games.table.update(GAME)

    await remove_(games, interaction, GAME.name)

    assert games.table.get(GAME.guild_id, GAME.name) is None
    assert_responded(interaction, 'Removed')


async def test_remove_game_missing(games: GamesCommands) -> None:
    remove_ = extract(games.remove)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.remove, user='user', guild=guild)

    await remove_(games, interaction, GAME.name)

    assert_responded(interaction, 'does not exist')


async def test_roll_games(games: GamesCommands) -> None:
    roll_ = extract(games.roll)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.roll, user='user', guild=guild)

    games.table.update(GAME._replace(name='Game A'))
    games.table.update(GAME._replace(name='Game B'))
    games.table.update(GAME._replace(guild_id=42, name='Game C'))

    await roll_(games, interaction)

    message = assert_responded(interaction, 'Game')
    assert 'Game A' in message or 'Game B' in message
    assert 'Game C' not in message


async def test_roll_games_empty(games: GamesCommands) -> None:
    roll_ = extract(games.roll)

    guild = MockGuild('guild', GAME.guild_id)
    interaction = MockInteraction(games.roll, user='user', guild=guild)

    await roll_(games, interaction)

    assert_responded(interaction, 'No games')
