import discord
import json
import os

from discord.ext import commands
from typing import Any, Dict, Optional

from threepseat.bot import Bot
from threepseat.utils import is_admin, keys_to_int


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
        """
        Args:
            bot (Bot): bot that loaded this cog
            mc_file (str): path to store json data
        """
        self.bot = bot
        self.mc_dict = {}
        self.mc_file = mc_file

        if os.path.exists(self.mc_file):
            with open(self.mc_file) as f:
                self.mc_dict = keys_to_int(json.load(f))

    async def mc(self, ctx: commands.Context) -> None:
        """Message `ctx.channel` with Minecraft server info

        Args:
            ctx (Context): context from command call
        """
        if ctx.guild.id not in self.mc_dict:
            await self.bot.message_guild(
                    'there is no minecraft server on this guild.',
                    ctx.channel)
        else:
            server_info = self.mc_dict[ctx.guild.id]
            if not ('name' in server_info and 'address' in server_info):
                await self.bot.message_guild(
                        'server name and address have not been set yet', 
                        ctx.channel)
                return
            msg = 'To login to the {} server:\n'.format(
                    server_info['name'])
            msg += ' - join the server using IP: {}\n'.format(
                    server_info['address'])
            if 'has_whitelist' in server_info and 'admin_id' in server_info:
                if server_info['has_whitelist'] and server_info['admin_id'] is not None:
                    msg += ' - message <@{}> for whitelist'.format(
                            server_info['admin_id'])
            await self.bot.message_guild(msg, ctx.channel)

    async def clear(self, ctx: commands.Context) -> None:
        """Clear Mincraft server info for `ctx.guild`

        Args:
            ctx (Context): context from command call
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id in self.mc_dict:
                del self.mc_dict[ctx.guild.id]
                self.save_servers()
                await self.bot.message_guild(
                    'cleared Minecraft server info', ctx.channel)
            else:
                await self.bot.message_guild(
                    'there is no Mincraft server currently', ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)

    async def name(self, ctx: commands.Context, name: str) -> None:
        """Change Minecraft server name for the guild

        Args:
            ctx (Context): context from command call
            name (str): new server name
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['name'] = name
            self._save_servers()
            await self.bot.message_guild(
                    'updated server name to: {}'.format(name),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)

    async def address(self, ctx: commands.Context, address: str) -> None:
        """Change Minecraft server name for the guild

        Args:
            ctx (Context): context from command call
            address (str): new ip address
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['address'] = address
            self._save_servers()
            await self.bot.message_guild(
                    'updated server address to: {}'.format(address),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)

    async def whitelist(self, ctx: commands.Context, has_whitelist: bool) -> None:
        """Change Minecraft server name for the guild

        Args:
            ctx (Context): context from command call
            has_whitelist (bool): if the server has a whitelist
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['has_whitelist'] = has_whitelist
            self._save_servers()
            await self.bot.message_guild(
                    'updated server whitelist to: {}'.format(has_whitelist),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)

    async def admin(self, ctx: commands.Context, member: discord.Member) -> None:
        """Change Minecraft server name for the guild

        The "admin" is the guild member that will be mentioned for contact
        if there is a whitelist on the server.

        Args:
            ctx (Context): context from command call
            member (Member): member to set as Minecraft server admin
        """
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['admin_id'] = member.id
            self._save_servers()
            await self.bot.message_guild(
                    'updated server admin to: {}'.format(member.mention),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)

    def _save_servers(self) -> None:
        """Write server data to file"""
        with open(self.mc_file, 'w') as f:
            json.dump(self.mc_dict, f, indent=4, sort_keys=True)

    @commands.group(name='mc', pass_context=True, brief='Minecraft server info')
    async def _mc(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.mc(ctx)

    @_mc.command(name='clear', pass_context=True, brief='clear Minecraft info')
    async def _clear(self, ctx: commands.Context) -> None:
        await self.clear(ctx)

    @_mc.group(name='set', pass_context=True, brief='update Minecraft info')
    async def _set(self, ctx: commands.Context) -> None:
        # TODO: should we message here with the set options?
        pass

    @_set.command(name='name', pass_context=True, brief='set Minecraft server name')
    async def _name(self, ctx: commands.Context, name: str) -> None:
        await self.name(ctx, name)

    @_set.command(name='address', pass_context=True, brief='set Minecraft server address')
    async def _address(self, ctx: commands.Context, address: str) -> None:
        await self.address(ctx, address)

    @_set.command(name='whitelist', pass_context=True, brief='set Minecraft server whitelist')
    async def _whitelist(self, ctx: commands.Context, has_whitelist: bool) -> None:
        await self.whitelist(ctx, has_whitelist)

    @_set.command(name='admin', pass_context=True, brief='set Minecraft server admin')
    async def _admin(self, ctx: commands.Context, member: discord.Member) -> None:
        await self.admin(ctx, member)