from __future__ import annotations

import logging
import random
import time

import discord
from discord import app_commands

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.ext.extension import CommandGroupExtension
from threepseat.ext.extension import MAX_CHOICES_LENGTH
from threepseat.ext.games.data import Game
from threepseat.ext.games.data import GamesTable

logger = logging.getLogger(__name__)


class GamesCommands(CommandGroupExtension):
    """App commands group for managing list of games to play."""

    def __init__(self, db_path: str) -> None:
        """Init GamesCommands.

        Args:
            db_path (str): path to database to use.
        """
        self.table = GamesTable(db_path)

        super().__init__(
            name='games',
            description='Manage list of games to play',
            guild_only=True,
        )

    async def autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Return list of games in a guild."""
        assert interaction.guild is not None
        games = self.table.all(interaction.guild.id)
        choices = [
            app_commands.Choice(name=game.name, value=game.name)
            for game in games
            if current.lower() in game.name.lower() or current == ''
        ]
        choices = sorted(choices, key=lambda c: c.name.lower())
        return choices[: min(len(choices), MAX_CHOICES_LENGTH)]

    @app_commands.command(
        name='add',
        description='[Admin Only] Add a new game to the list',
    )
    @app_commands.describe(name='Name of the game to add')
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def add(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 1, 40],
    ) -> None:
        """Add a game to the list for the guild."""
        assert interaction.guild is not None

        existing = self.table.get(interaction.guild.id, name)
        if existing is not None:
            await interaction.response.send_message(
                f'A game named {name} already exists.',
                ephemeral=True,
            )
            return

        game = Game(
            guild_id=interaction.guild.id,
            author_id=interaction.user.id,
            creation_time=int(time.time()),
            name=name,
        )
        self.table.update(game)

        await interaction.response.send_message(
            f'Added {name} to the list.',
            ephemeral=True,
        )

    @app_commands.command(name='list', description='List all the games')
    @app_commands.check(log_interaction)
    async def list(self, interaction: discord.Interaction) -> None:
        """List games in the guild."""
        assert interaction.guild is not None

        games = self.table.all(interaction.guild.id)
        if len(games) == 0:
            await interaction.response.send_message(
                'No games have been added yet.',
                ephemeral=True,
            )
            return

        game_names = [g.name for g in games]
        game_names.sort()
        game_str = '\n'.join(game_names)

        await interaction.response.send_message(
            f'Available games:\n```\n{game_str}\n```',
        )

    @app_commands.command(
        name='remove',
        description='[Admin Only] Remove a game from the list',
    )
    @app_commands.describe(name='Name of the game to remove')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def remove(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Remove a game from the guild."""
        assert interaction.guild is not None

        removed = bool(self.table.remove(interaction.guild.id, name))
        if removed:
            await interaction.response.send_message(
                f'Removed {name} from the list.',
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f'A game named {name} does not exist.',
                ephemeral=True,
            )

    @app_commands.command(name='roll', description='Roll a random game')
    @app_commands.check(log_interaction)
    async def roll(self, interaction: discord.Interaction) -> None:
        """Roll a game in the guild."""
        assert interaction.guild is not None

        games = self.table.all(interaction.guild.id)
        if len(games) == 0:
            await interaction.response.send_message(
                'No games have been added yet.',
                ephemeral=True,
            )
            return

        game = random.choice(games)
        await interaction.response.send_message(f'You rolled {game.name}!')
