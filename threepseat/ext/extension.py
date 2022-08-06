from __future__ import annotations

import discord
from discord import app_commands


class CommandGroupExtension(app_commands.Group):
    """Base class for 3pseatBot command group extensions."""

    async def post_init(self, bot: discord.ext.commands.Bot) -> None:
        """Complete post initialization using a bot.

        This method should typically be called once after the extension
        and the bot/client have been initialized.

        Subclasses can use this method to launch background tasks that need
        the client, register commands, etc.
        """
        pass
