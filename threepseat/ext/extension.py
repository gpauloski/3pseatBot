from __future__ import annotations

import logging

import discord
from discord import app_commands

MAX_CHOICES_LENGTH = 25


class CommandGroupExtension(app_commands.Group):
    """Base class for 3pseatBot command group extensions."""

    async def post_init(self, bot: discord.ext.commands.Bot) -> None:
        """Complete post initialization using a bot.

        This method should only be called once after the extension
        and the bot/client have been initialized.

        Subclasses can use this method to launch background tasks that need
        the client, register commands, etc.
        """

    async def on_error(
        self,
        interaction: discord.Interaction[discord.Client],
        error: app_commands.AppCommandError,
    ) -> None:
        """Callback for errors in child commands.

        Check failures carry a user-facing message (e.g. "you must be an
        admin"), so send those back to the caller; anything else is a bug and
        gets logged with a traceback.
        """
        # Attribute the log to the subclass's module rather than this one.
        logger = logging.getLogger(type(self).__module__)
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(str(error), ephemeral=True)
            logger.info('app command check failed: %s', error)
        else:
            logger.exception(error)

    async def post_shutdown(self) -> None:
        """Release resources held by the extension.

        Mirror of post_init(), called once while the bot is shutting down.
        Subclasses can use this method to cancel background tasks, close
        database connections, etc.
        """
