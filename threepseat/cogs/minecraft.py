"""Cog for Minecraft server command"""
import discord

from discord.ext import commands

from threepseat.bot import Bot
from threepseat.utils import is_admin, GuildDatabase


class Minecraft(commands.Cog):
    """Extension for commands for a guild Minecraft server

    Adds the following commands:
      - `?mc`: provides the Minecraft server information for the guild
      - `?mc clear`: clear Minecraft server information for the guild
      - `?mc set name [str]`: set name of Minecraft server
      - `?mc set address [str]`: set ip address of Minecraft server
      - `?mc set whitelist [bool]`: set if server has a whitelist
      - `?mc set admin @Member`: admin of server to message for whitelist

    Attributes:
        mc_dict (dict): dict indexed by guild IDs with values corresponding
            to dicts of the form: :code:`{name: str, address: str,
            has_whitelist: bool, admin_id: int}`.
    """

    def __init__(self, bot: Bot, mc_file: str) -> None:
        """Init Minecraft

        Args:
            bot (Bot): bot that loaded this cog
            mc_file (str): path to store database
        """
        self.bot = bot
        self.db = GuildDatabase(mc_file)

    async def mc(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with Minecraft server info

        Args:
            ctx (Context): context from command call
        """
        if not self._server_exists(ctx.guild):
            await self.bot.message_guild(
                'there is no minecraft server on this guild. '
                'Use `mc set name [name]` and `mc set address [ip]` '
                'to set one',
                ctx.channel,
            )
        else:
            name = self.db.value(ctx.guild, 'name')
            address = self.db.value(ctx.guild, 'address')
            has_whitelist = self.db.value(ctx.guild, 'has_whitelist')
            admin_id = self.db.value(ctx.guild, 'admin_id')
            msg = 'To login to the {} server:\n'.format(name)
            msg += ' - join the server using IP: {}\n'.format(address)
            if has_whitelist is True and admin_id is not None:
                msg += ' - message <@{}> for whitelist'.format(admin_id)
            await self.bot.message_guild(msg, ctx.channel)

    async def clear(self, ctx: commands.Context) -> None:
        """Clear Mincraft server info for `ctx.guild`

        Args:
            ctx (Context): context from command call
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            self.db.drop_table(ctx.guild)
            await self.bot.message_guild(
                'cleared Minecraft server info', ctx.channel
            )
        else:
            raise commands.MissingPermissions

    async def address(self, ctx: commands.Context, address: str) -> None:
        """Change Minecraft server name for the guild

        Args:
            ctx (Context): context from command call
            address (str): new ip address
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            self.db.set(ctx.guild, 'address', address)
            await self.bot.message_guild(
                'updated server address to: {}'.format(address), ctx.channel
            )
        else:
            raise commands.MissingPermissions

    async def admin(
        self, ctx: commands.Context, member: discord.Member
    ) -> None:
        """Change Minecraft server name for the guild

        The "admin" is the guild member that will be mentioned for contact
        if there is a whitelist on the server.

        Args:
            ctx (Context): context from command call
            member (Member): member to set as Minecraft server admin
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            self.db.set(ctx.guild, 'admin_id', member.id)
            await self.bot.message_guild(
                'updated server admin to: {}'.format(member.mention),
                ctx.channel,
            )
        else:
            raise commands.MissingPermissions

    async def name(self, ctx: commands.Context, name: str) -> None:
        """Change Minecraft server name for the guild

        Args:
            ctx (Context): context from command call
            name (str): new server name
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            self.db.set(ctx.guild, 'name', name)
            await self.bot.message_guild(
                'updated server name to: {}'.format(name), ctx.channel
            )
        else:
            raise commands.MissingPermissions

    async def whitelist(
        self, ctx: commands.Context, has_whitelist: bool
    ) -> None:
        """Change Minecraft server name for the guild

        Args:
            ctx (Context): context from command call
            has_whitelist (bool): if the server has a whitelist
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            self.db.set(ctx.guild, 'has_whitelist', has_whitelist)
            await self.bot.message_guild(
                'updated server whitelist to: {}'.format(has_whitelist),
                ctx.channel,
            )
        else:
            raise commands.MissingPermissions

    def _server_exists(self, guild: discord.Guild) -> bool:
        """Check if guild has server info

        The name and address are required for the server to be valid.
        """
        return (
            self.db.value(guild, 'name') is not None
            and self.db.value(guild, 'address') is not None
        )

    @commands.group(
        name='mc',
        pass_context=True,
        brief='Minecraft server info',
        description='Manage and see Minecraft server info for the guild. '
        'Calling mc on its own will print the server info.',
    )
    async def _mc(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.mc(ctx)

    @_mc.command(
        name='clear',
        pass_context=True,
        brief='clear Minecraft info',
        ignore_extra=False,
        description='Remove all info about the Mincraft server for the guild.',
    )
    async def _clear(self, ctx: commands.Context) -> None:
        await self.clear(ctx)

    @_mc.group(
        name='set',
        pass_context=True,
        brief='update Minecraft info',
        description='Update the Minecraft server info. Note that at minimum, '
        'the name and address must be specified.',
    )
    async def _set(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.bot.message_guild(
                'use one of the subcommands (address/admin/name/whitelist) '
                'to set that value',
                ctx.channel,
            )

    @_set.command(
        name='address',
        pass_context=True,
        brief='set Minecraft server IP address',
        description='Set the IP address used to connect to the server',
    )
    async def _address(self, ctx: commands.Context, *, address: str) -> None:
        await self.address(ctx, address)

    @_set.command(
        name='admin',
        pass_context=True,
        brief='set Minecraft server admin',
        ignore_extra=False,
        description='Set the admin of the Minecraft server. Note this should '
        'be a mention and is only used if whitelist is also set '
        'to true.',
    )
    async def _admin(
        self, ctx: commands.Context, member: discord.Member
    ) -> None:
        await self.admin(ctx, member)

    @_set.command(
        name='name',
        pass_context=True,
        brief='set Minecraft server name',
        description='Set name of Minecraft server. Note quotations around the '
        'name are not necessary',
    )
    async def _name(self, ctx: commands.Context, *, name: str) -> None:
        await self.name(ctx, name)

    @_set.command(
        name='whitelist',
        pass_context=True,
        brief='set Minecraft server whitelist',
        ignore_extra=False,
        description='Set the flag for if the server has a whitelist. I.e. '
        '<whitelist>=true|false. If true, a server admin must '
        'also be set.',
    )
    async def _whitelist(
        self, ctx: commands.Context, has_whitelist: bool
    ) -> None:
        await self.whitelist(ctx, has_whitelist)
