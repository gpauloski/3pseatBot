import discord
import json
import os

from discord.ext import commands
from typing import Any, Dict, Optional

from threepseat.utils import is_admin, keys_to_int


class Minecraft(commands.Cog):
    """Extension for commands for a guild Minecraft server

    Data is stored in `self.mc_dict`, a dict with structure:
        {
            int(guild_id): {
                'name': str(mc_server_name),
                'address': str(mc_server_address),
                'has_whitelist': bool,
                'admin': Optional[int(user_id)]
            },
            ...
        }
    """
    def __init__(self, bot: commands.Bot, mc_file: str) -> None:
        self.bot = bot
        self.mc_dict = {}
        self.mc_file = mc_file

        if os.path.exists(self.mc_file):
            with open(self.mc_file) as f:
                self.mc_dict = keys_to_int(json.load(f))


    @commands.group(pass_context=True, brief='Minecraft server info')
    async def mc(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
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


    @mc.command(pass_context=True, brief='clear Minecraft info')
    async def clear(self, ctx: commands.Context) -> None:
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id in self.mc_dict:
                del self.mc_dict[ctx.guild.id]
                self.save_config()
                await self.bot.message_guild(
                    'cleared Minecraft server info', ctx.channel)
            else:
                await self.bot.message_guild(
                    'there is no Mincraft server currently', ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)


    @mc.group(pass_context=True, brief='update Minecraft info')
    async def set(self, ctx: commands.Context) -> None:
        pass


    @set.command(pass_context=True, brief='set Minecraft server name')
    async def name(self, ctx: commands.Context, name: str) -> None:
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['name'] = name
            self.save_config()
            await self.bot.message_guild(
                    'updated server name to: {}'.format(name),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)


    @set.command(pass_context=True, brief='set Minecraft server address')
    async def address(self, ctx: commands.Context, address: str) -> None:
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['address'] = address
            self.save_config()
            await self.bot.message_guild(
                    'updated server address to: {}'.format(address),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)


    @set.command(pass_context=True, brief='set Minecraft server whitelist')
    async def whitelist(self, ctx: commands.Context, has_whitelist: bool) -> None:
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['has_whitelist'] = has_whitelist
            self.save_config()
            await self.bot.message_guild(
                    'updated server whitelist to: {}'.format(has_whitelist),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)


    @set.command(pass_context=True, brief='set Minecraft server admin')
    async def admin(self, ctx: commands.Context, member: discord.Member) -> None:
        if is_admin(ctx.author) or self.bot.is_bot_admin(ctx.author):
            if ctx.guild.id not in self.mc_dict:
                self.mc_dict[ctx.guild.id] = {}
            self.mc_dict[ctx.guild.id]['admin_id'] = member.id
            self.save_config()
            await self.bot.message_guild(
                    'updated server admin to: {}'.format(member.mention),
                    ctx.channel)
        else:
            await self.bot.message_guild(
                    'this command requires admin power',
                    ctx.channel)


    def save_config(self) -> None:
        with open(self.mc_file, 'w') as f:
            json.dump(self.mc_dict, f, indent=4, sort_keys=True)
