from __future__ import annotations

import logging
import time
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands as ext_commands

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.ext.custom.data import CustomCommand
from threepseat.ext.custom.data import CustomCommandTable
from threepseat.ext.extension import CommandGroupExtension
from threepseat.ext.extension import MAX_CHOICES_LENGTH
from threepseat.utils import alphanumeric

logger = logging.getLogger(__name__)


class CustomCommands(CommandGroupExtension):
    """Custom commands group."""

    def __init__(self, db_path: str) -> None:
        """Init CustomCommands.

        Warning:
            post_init() should be called after initializing
            a new object to ensure all commands in the database get
            registered.

        Args:
            db_path (str): path to database file.
        """
        self.table = CustomCommandTable(db_path)

        super().__init__(
            name='commands',
            description='Create custom commands',
            guild_only=True,
        )

    async def post_init(self, bot: discord.ext.commands.Bot) -> None:
        """Register all saved custom commands to the client."""
        for command in self.table.all():
            await self.register(command, bot, sync=False)

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

    async def autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Return list of custom commands in the guild matching current."""
        assert interaction.guild is not None
        choices = [
            app_commands.Choice(name=command.name, value=command.name)
            for command in self.table.all(interaction.guild.id)
            if current.lower() in command.name.lower() or current == ''
        ]
        choices = sorted(choices, key=lambda c: c.name.lower())
        return choices[: min(len(choices), MAX_CHOICES_LENGTH)]

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
        name: app_commands.Range[str, 1, 18],
        description: app_commands.Range[str, 1, 50],
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

        self.table.update(command)
        await self.register(command, interaction.client)

        await interaction.followup.send(f'Created /{name}.', ephemeral=True)

    @app_commands.command(name='list', description='List custom commands')
    @app_commands.check(log_interaction)
    async def list(self, interaction: discord.Interaction) -> None:
        """List custom commands."""
        assert interaction.guild is not None
        commands = self.table.all(interaction.guild.id)

        if len(commands) == 0:
            await interaction.response.send_message(
                'The guild has no custom commands.',
                ephemeral=True,
            )
        else:
            names = [command.name for command in commands]
            name_list = ', '.join(names)

            await interaction.response.send_message(
                f'This guild has these custom commands: {name_list}.',
                ephemeral=True,
            )

    @app_commands.command(
        name='remove',
        description='[Admin Only] Remove a custom command',
    )
    @app_commands.describe(name='Name of command to remove')
    @app_commands.autocomplete(name=autocomplete)
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

        removed = bool(self.table.remove(interaction.guild.id, name))
        if removed:
            await self.unregister(name, interaction.guild, interaction.client)
            await interaction.followup.send(
                f'Removed /{name}.',
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f'The command /{name} does not exist.',
                ephemeral=True,
            )

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
