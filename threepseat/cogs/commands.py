"""Custom Commands Cog"""
import discord

from discord.ext import commands
from typing import Optional

from threepseat.bot import Bot
from threepseat.utils import is_admin, GuildDatabase


class Commands(commands.Cog):
    """Extension for custom commands.

    Adds the following commands:
      - `?command add [name] [command text]`
      - `?command remove [name]`
    """

    def __init__(
        self,
        bot: Bot,
        commands_file: str,
        guild_admin_permission: bool = True,
        bot_admin_permission: bool = True,
        everyone_permission: bool = False,
    ) -> None:
        """Init Commands

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

        # Register all commands on startup
        tables = self.db.tables()
        for table in tables.values():
            for name, text in table.items():
                self.bot.add_command(self.make_command(name, text))

    def has_permission(self, member: discord.Member) -> bool:
        """Does a member have permission to edit commands"""
        if self.everyone_permission:
            return True
        if is_admin(member) or self.bot.is_bot_admin(member):
            return True
        return False

    def is_custom_command(self, cmd: commands.Command) -> bool:
        """Check if command was created by this cog"""
        if cmd.cog_name == 'custom_commands':
            return True
        if 'cog_name' in cmd.__original_kwargs__:
            return cmd.__original_kwargs__['cog_name'] == 'custom_commands'
        return False

    def make_command(self, name: str, text: str) -> commands.Command:
        """Create Discord Command

        Args:
            name (str): name of command
            text (str): message to return when command is executed

        Returns:
            Command
        """

        async def _command(_ctx: commands.Context):
            _text = self._get_command(_ctx.guild, name)
            if _text is None:
                await self.bot.message_guild(
                    'this command is not available in this guild', _ctx.channel
                )
            else:
                await self.bot.message_guild(_text, _ctx.channel)

        return commands.Command(
            _command, name=name, cog_name='custom_commands'
        )

    async def add(self, ctx: commands.Context, name: str, text: str) -> None:
        """Add a new command to the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): name of command
            text (str): text of command
        """
        if not self.has_permission(ctx.message.author):
            raise commands.MissingPermissions

        # Check if this is a custom command that can be overwritten if
        # it exists
        cmd = self.bot.get_command(name)
        if cmd is not None:
            if self.is_custom_command(cmd):
                self.bot.remove_command(name)
            else:
                await self.bot.message_guild(
                    'this command already exist and cannot be overwritten',
                    ctx.channel,
                )
                return

        # Save to database
        self._set_command(ctx.guild, name, text)
        # Register with bot
        self.bot.add_command(self.make_command(name, text))

        await self.bot.message_guild(
            'added command {}{}'.format(self.bot.command_prefix, name),
            ctx.channel,
        )

    async def remove(self, ctx: commands.Context, name: str) -> None:
        """Remove a command from the guild

        Sends a message to `ctx.channel` on success or failure.

        Args:
            ctx (Context): context from command call
            name (str): name of command to remove
        """
        if not self.has_permission(ctx.message.author):
            raise commands.MissingPermissions

        cmd = self.bot.get_command(name)
        if cmd is not None:
            # Only remove if it is a custom command
            if self.is_custom_command(cmd):
                # Remove from bot
                self.bot.remove_command(name)
                # Remove from database
                self._remove_command(ctx.guild, name)
                msg = 'removed command {}{}'.format(
                    self.bot.command_prefix, name
                )
                await self.bot.message_guild(msg, ctx.channel)
            else:
                await self.bot.message_guild(
                    'this command cannot be removed', ctx.channel
                )
                return
        else:
            await self.bot.message_guild(
                'the {} command does not exists'.format(name), ctx.channel
            )

    def _get_command(self, guild: discord.Guild, name: str) -> Optional[str]:
        """Get command text from database"""
        return self.db.value(guild, name)

    def _remove_command(self, guild: discord.Guild, name: str) -> None:
        """Remove command text from database"""
        return self.db.clear(guild, name)

    def _set_command(self, guild: discord.Guild, name: str, text: str) -> None:
        """Set command in dataset"""
        self.db.set(guild, name, text)

    @commands.group(
        name='commands',
        pass_context=True,
        brief='add/remove custom commands',
        description='Add and remove custom commands for this guild.',
    )
    async def _commands(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.bot.message_guild(
                'use the `add` or `remove` subcommands. See `{}help {}` for '
                'more info'.format(self.bot.command_prefix, ctx.invoked_with),
                ctx.channel,
            )

    @_commands.command(
        name='add',
        pass_context=True,
        brief='add a custom command',
        description='Add a custom command that can be invoked with <name>. '
        'The command will print all <text> after <name>. '
        'Note that quotes are not needed around the command body '
        'text.',
    )
    async def _add(
        self, ctx: commands.Context, name: str, *, text: str
    ) -> None:
        await self.add(ctx, name, text)

    @_commands.command(
        name='remove',
        pass_context=True,
        brief='remove a custom command',
        ignore_extra=False,
        description='Remove the custom command with <name>',
    )
    async def _remove(self, ctx: commands.Context, name: str) -> None:
        await self.remove(ctx, name)
