from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import time
from collections.abc import Generator
from typing import Any
from typing import NamedTuple

import discord
from discord import app_commands
from discord.ext import commands as ext_commands

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.database import create_table
from threepseat.database import named_tuple_parameters
from threepseat.utils import alphanumeric

logger = logging.getLogger(__name__)


class CustomCommand(NamedTuple):
    """Row for custom command in database."""

    name: str
    description: str
    body: str
    author_id: int
    guild_id: int
    creation_time: float


class CustomCommands(app_commands.Group):
    """Custom commands group."""

    def __init__(self, db_path: str) -> None:
        """Init CustomCommands.

        Warning:
            register_all() should be called after initializing
            a new object to ensure all commands in the database get
            registered.

        Args:
            db_path (str): path to database file.
        """
        self.db_path = db_path

        if len(os.path.dirname(self.db_path)) > 0:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self.connect() as db:
            create_table(db, 'custom_commands', CustomCommand)

        super().__init__(
            name='commands',
            description='Create custom commands',
            guild_only=True,
        )

    @contextlib.contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Database connection context manager."""
        # Source: https://github.com/pre-commit/pre-commit/blob/354b900f15e88a06ce8493e0316c288c44777017/pre_commit/store.py#L91  # noqa: E501
        with contextlib.closing(sqlite3.connect(self.db_path)) as db:
            with db:
                yield db

    async def register(
        self,
        command: CustomCommand,
        bot: ext_commands.Bot,
        sync: bool = True,
    ) -> None:
        """Register app command with bot.

        Args:
            command (CustomCommand): command to register.
            bot (Bot): bot to register command using.
            sync (bool): force sync guild commands.
        """

        @app_commands.guild_only
        @app_commands.check(log_interaction)
        async def _callback(
            interaction: discord.Interaction,
        ) -> None:  # pragma: no cover
            await interaction.response.send_message(command.body)

        command_: Any = app_commands.Command(
            name=command.name,
            description=command.description,
            callback=_callback,
        )

        guild = bot.get_guild(command.guild_id)
        bot.tree.remove_command(command.name, guild=guild)
        bot.tree.add_command(command_, guild=guild)
        if sync:
            await bot.tree.sync(guild=guild)
        logger.info(
            f'registered custom command /{command.name} in {guild.name} '
            f'({command.guild_id}) (sync={sync})',
        )

    async def unregister(
        self,
        name: str,
        guild: discord.Guild,
        bot: ext_commands.Bot,
    ) -> None:
        """Unregister app command from bot."""
        bot.tree.remove_command(name, guild=guild)
        await bot.tree.sync(guild=guild)
        logger.info(
            f'unregistered custom command /{name} from '
            f'{guild.name} ({guild.id})',
        )

    async def register_all(
        self,
        bot: ext_commands.Bot,
        sync: bool = False,
    ) -> None:
        """Register all commands in the database."""
        for command in self.list_in_db():
            await self.register(command, bot, sync)

    def add_to_db(self, command: CustomCommand) -> None:
        """Add command to the table."""
        params = named_tuple_parameters(CustomCommand)
        with self.connect() as db:
            db.execute(
                f'INSERT INTO custom_commands VALUES {params}',
                command._asdict(),
            )

    def list_in_db(self, guild_id: int | None = None) -> list[CustomCommand]:
        """Get list of custom commands in guild."""
        with self.connect() as db:
            if guild_id is not None:
                rows = db.execute(
                    'SELECT * FROM custom_commands WHERE guild_id = :guild_id',
                    {'guild_id': guild_id},
                ).fetchall()
            else:
                rows = db.execute('SELECT * FROM custom_commands').fetchall()
        return [CustomCommand(*row) for row in rows]

    def remove_from_db(self, name: str, guild_id: int) -> None:
        """Remove a custom command from the guild."""
        with self.connect() as db:
            db.execute(
                'DELETE FROM custom_commands '
                'WHERE guild_id = :guild_id AND name = :name',
                {'guild_id': guild_id, 'name': name},
            )

    @app_commands.command(
        name='create',
        description='[Admin Only] Create a custom command',
    )
    @app_commands.describe(name='Name of command (must be a single word)')
    @app_commands.describe(description='Command description')
    @app_commands.describe(body='Body of command')
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        description: str,
        body: str,
    ) -> None:
        """Create a custom command."""
        if not alphanumeric(name) or len(name) == 0:
            await interaction.response.send_message(
                'The command name must be a single word with only '
                'alphanumeric characters.',
            )
            return

        await interaction.response.defer(thinking=True)

        assert interaction.guild is not None
        command = CustomCommand(
            name=name,
            description=description,
            body=body,
            guild_id=interaction.guild.id,
            author_id=interaction.user.id,
            creation_time=time.time(),
        )

        self.add_to_db(command)
        await self.register(command, interaction.client)

        await interaction.followup.send(f'Created /{name}')

    @app_commands.command(name='list', description='List custom commands')
    @app_commands.check(log_interaction)
    async def list(self, interaction: discord.Interaction) -> None:
        """List custom commands."""
        assert interaction.guild is not None
        commands = self.list_in_db(interaction.guild.id)

        if len(commands) == 0:
            await interaction.response.send_message(
                'The guild has no custom commands.',
            )
        else:
            names = [command.name for command in commands]
            name_list = ', '.join(names)

            await interaction.response.send_message(
                f'This guild has these custom commands: {name_list}.',
            )

    @app_commands.command(
        name='remove',
        description='[Admin Only] Remove a custom command',
    )
    @app_commands.describe(name='Name of command to remove')
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def remove(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Remove a custom command."""
        await interaction.response.defer(thinking=True)

        assert interaction.guild is not None
        self.remove_from_db(name, interaction.guild.id)
        await self.unregister(name, interaction.guild, interaction.client)

        await interaction.followup.send(f'Removed /{name}')

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Callback for errors in child functions."""
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(str(error), ephemeral=True)
            logger.info(f'app command check failed: {error}')
        else:
            logger.exception(error)
