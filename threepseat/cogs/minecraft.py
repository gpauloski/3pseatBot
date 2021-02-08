import json
import os

from discord.ext import commands

class Minecraft(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {'name': 'none', 'ip': 'none'}
        self.config_file = 'data/mc_config.json'
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file) as f:
                self.config = json.load(f)

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    async def _is_allowed_in_guild(self, ctx):
        if ctx.message.guild.name not in self.bot.whitelist_guilds:
            await self.bot.send_server_message(ctx.channel, 
                    'This command is not authorized on this server')
            return False
        return True

    @commands.command(name='mc', pass_context=True,
                      brief='Minecraft Server Login')
    async def _mc(self, ctx):
        if (await self._is_allowed_in_guild(ctx)):
            admin = self.bot.get_user(ctx.guild, self.bot.admins[0])
            msg = ('To login to the {} server:\n'
                   '(1) Join the server using IP: {}\n'
                   '(2) Message {} for whitelist'.format(
                   self.config['name'], self.config['ip'], admin.mention))
            await self.bot.send_server_message(ctx.channel, msg)

    @commands.command(name='mcname', pass_context=True,
                      brief='Update Minecraft Server name')
    async def _change_name(self, ctx, name):
        if (await self._is_allowed_in_guild(ctx) and 
            self.bot.is_admin(ctx.guild, ctx.message.author)):
            self.config['name'] = name
            self.save_config()
            await self.bot.send_server_message(ctx.channel,
                    'Updated name to {}.'.format(name))

    @commands.command(name='mcip', pass_context=True,
                      brief='Update Minecraft Server IP')
    async def _change_ip(self, ctx, ip):
        if (await self._is_allowed_in_guild(ctx) and 
            self.bot.is_admin(ctx.guild, ctx.message.author)):
            self.config['ip'] = ip
            self.save_config()
            await self.bot.send_server_message(ctx.channel,
                    'Updated IP to {}.'.format(ip))