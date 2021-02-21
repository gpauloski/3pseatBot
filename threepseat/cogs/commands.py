import discord
import json
import os
import random

from discord.ext import commands
from typing import Any, Callable, List, Optional

from threepseat.bot import Bot
from threepseat.utils import is_admin, GuildDatabase


class Commands(commands.Cog):
    """Extension for custom commands.

    Adds the following commands:
      - `?command add [name] [command text]
      - `?command remove [name]
    """
    def __init__(self,
                 bot: Bot,
                 commands_file: str,
                 guild_admin_permission: bool = True,
                 bot_admin_permission: bool = True,
                 everyone_permission: bool = False
    ) -> None:
        """
        Args:
            bot (Bot): bot that loaded this cog
            commands_file (str): path to store database
            guild_admin_permission (bool): can guild admins start polls
            bot_admin_permission (bool): can bot admin start polls
            everyone_permission (bool): allow everyone to start polls
        """
        self.bot = bot
        self.guild_admin_permission = guild_admin_permission
        self.bot_admin_permission = bot_admin_permission
        self.everyone_permission = everyone_permission
        self.db = GuildDatabase(commands_file)

    def has_permission(self, member: discord.Member) -> bool:
        """Does a member have permission to edit commands"""
        if self.everyone_permission:
            return True
        if is_admin(member) or self.bot.is_bot_admin(member):
            return True
        return False

    async def add(self, ctx: commands.Context, name: str, text: str) -> None:
        """Add a new command to the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): name of command
            text (str): text of command
        """
        if not self.has_permission(ctx.message.author):
            await self.bot.message_guild(
                '{}, you do not have permission to add a command'.format(
                    ctx.message.author.mention),
                ctx.channel)
            return

        self._set_command(ctx.guild, name, text)

        # If the rules cogs is laoded, we want the rules cog to ignore
        # this command and let this cog handle the CommandNotFound error
        rules_cog = self.bot.get_cog('Rules')
        if rules_cog is not None:
            rules_cog.whitelist_prefix.append(self.bot.command_prefix + name)

        await self.bot.message_guild(
                'added command {}{}'.format(self.bot.command_prefix, name),
                ctx.channel)

    async def remove(self, ctx: commands.Context, name: str) -> None:
        """Remove a command from the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): name of command to remove
        """
        if not self.has_permission(ctx.message.author):
            await self.bot.message_guild(
                '{}, you do not have permission to remove a command'.format(
                    ctx.message.author.mention),
                ctx.channel)
            return

        self._remove_command(ctx.guild, name)

        rules_cog = self.bot.get_cog('Rules')
        if rules_cog is not None:
            rules_cog.whitelist_prefix.remove(self.bot.command_prefix + name)

        await self.bot.message_guild(
                'removed command {}{}'.format(self.bot.command_prefix, name),
                ctx.channel)

    def _get_command(self, guild: discord.Guild, name: str) -> Optional[str]:
        """Get command text from database"""
        return self.db.value(guild, name)

    def _remove_command(self, guild: discord.Guild, name: str) -> None:
        """Remove command text from database"""
        return self.db.clear(guild, name)

    def _set_command(self, guild: discord.Guild, name: str, text: str) -> None:
        """Set command in dataset"""
        self.db.set(guild, name, text)

    @commands.Cog.listener()
    async def on_command_error(self,
                               ctx: commands.Context,
                               error: commands.CommandError
        ) -> None:
        """Catch CommandNotFound and check if user command

        Instead of registering custom commands to the cog with
        the command decorator, we instead catch all CommandNotFound
        errors and check if the attempted invoke command is one that
        has been added to the guild.

        Warning:
            Other cogs that listen to `on_command_error` will
            still capture the CommandNotFound error.

        Args:
            ctx (Context): context from command call
            error (CommandError): error raised by the API
        """
        if isinstance(error, commands.CommandNotFound):
            command_text = self._get_command(ctx.guild, ctx.invoked_with)
            if command_text is not None:
                if len(ctx.message.content.split(' ')) > 1:
                    await self.bot.message_guild(
                            'unknown additional arguments to {}{}'.format(
                                self.bot.command_prefix, ctx.invoked_with),
                            ctx.channel)
                    return
                else:
                    await self.bot.message_guild(command_text, ctx.channel)

    @commands.group(name='commands', pass_context=True, brief='?help commands for more info')
    async def _commands(self, ctx: commands.Context) -> None:
        pass

    @_commands.command(name='add', pass_context=True, brief='add a command')
    async def _add(self, ctx: commands.Context, name: str, *, text: str) -> None:
        await self.add(ctx, name, text)

    @_commands.command(name='remove', pass_context=True, brief='remove a command')
    async def _remove(self, ctx: commands.Context, name: str) -> None:
        await self.remove(ctx, name)