import configparser
import logging
import json
import inspect
import os
import re

import discord
import emoji

from bans import Bans
from discord.ext import	commands
from dotenv import load_dotenv

EXTENSIONS = ['cogs.general', 'cogs.games', 'cogs.minecraft', 'cogs.memes',
              'cogs.voice']
F_EMOJI = '\U0001F1EB'
EMOJI_RE = r'<:\w*:\d*>'
URL_RE = (r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.'
          '([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*')


class Bot(commands.AutoShardedBot):
    def __init__(self, config):
        self.command_prefix = '?'
        self.message_prefix = ['3pseat']
        self.whitelist_prefix = ['!']
        self.whitelist_guilds = []
        self.max_offenses = 3
        self.admins = []
        self.playing_title = None
        self.logger = logging.getLogger()

        self._parse_config(config)

        try:
            load_dotenv(dotenv_path='data/.env')
        except Exception as e:
            self.logger.warning('Error loading data/.env file.\n{}\n'.format(e))

        self.token = os.getenv('TOKEN')

        self.db = Bans()

        super().__init__(command_prefix=self.command_prefix)

    def _parse_config(self, config_file):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(config_file)
        self.command_prefix = config.get('Default', 'command_prefix')
        self.message_prefix = json.loads(config.get('Default', 'message_prefix'))
        self.whitelist_prefix = json.loads(config.get('Default', 'whitelist_prefix'))
        self.whitelist_guilds = json.loads(config.get('Default', 'whitelist_guilds'))
        self.max_offenses = config.getint('Default', 'max_offenses')
        self.admins = json.loads(config.get('Default', 'admins'))
        self.playing_title = config.get('Default', 'playing_title')

    def log(self, log_msg, level='info', guild_name=None, user_name=None):
        if guild_name is not None:
            log_msg = guild_name + ': ' + log_msg
        elif user_name is not None:
            log_msg = user_name + ': ' + log_msg
        if level == 'info':
            self.logger.info(log_msg)
        elif level == 'warning':
            self.logger.warning(log_msg)
        elif level == 'debug':
            self.logger.debug(log_msg)
        elif level == 'error':
            self.logger.error(log_msg)
        else:
            self.logger.error('Unknown logging level \'{}\''.format(level))

    async def send_direct_message(self, user, message):
        self.log(message, user_name=user.name)
        channel = await user.create_dm()
        msg = await channel.send(message)
        return msg

    async def send_server_message(self, channel, message, react_emoji=None):
        self.log(message, guild_name=channel.guild.name)
        msg = self.message_prefix[0] + ' ' + message
        msg = await channel.send(msg)
        if react_emoji is not None:
            if isinstance(react_emoji, str):
                await msg.add_reaction(react_emoji)
            elif isinstance(react_emoji, list):
                for e in react_emoji:
                    await msg.add_reaction(e)
        return msg

    def get_user(self, guild, name):
        name = name.split('#')
        return discord.utils.get(guild.members, name=name[0],
                                 discriminator=name[1])

    def is_admin(self, guild, user):
        for admin in self.admins:
            admin_user = self.get_user(guild, admin)
            if user == admin_user:
                return True
        return False

    async def send_invite_kick(self, channel, user):
        try:
            link = await channel.create_invite(max_uses=1)
            await self.send_direct_message(user, 'Sorry we had to kick you. '
                    'Here is a link to rejoin: {}'.format(link))
        except Exception as e:
            self.logger.warning('Failed to send rejoin message to {}.'
                    'Caught exception: {}'.format(user, e))

    async def kick_player(self, guild, channel, user):
        msg = ('That\'s {} strikes, {}. I\'m sorry but your time as come. '
               'RIP.\n'.format(self.max_offenses, user.mention))
        if user.guild_permissions.administrator:
            msg += ('Failed to kick {}. Your cognizance is highly '
                    'acknowledged.'.format(user.mention))
        else:
            try:
                await self.send_invite_kick(channel, user)
                await guild.kick(user)
                msg += 'Press F to pay respects.'
            except Exception as e: 
                self.logger.warning('Failed to kick {}. Caught exception: '
                                    '{}'.format(user, e))
        await self.send_server_message(channel, msg, react_emoji=F_EMOJI)

    def add_strike(self, guild, user):
        return self.db.up(guild.name, user.name)

    def remove_strike(self, guild, user):
        return self.db.down(guild.name, user.name)

    def clear_strikes(self, guild, user):
        self.db.clear(guild.name, user.name)

    async def handle_mistake(self, message):
        count = self.add_strike(message.guild, message.author)
        if count < self.max_offenses:
            msg = '{}! You\'ve disturbed the spirits ({}/{})'.format(
                    message.author.mention, count, self.max_offenses)
            await self.send_server_message(message.channel, msg)
        else:
            self.clear_strikes(message.guild, message.author)
            await self.kick_player(message.guild, message.channel, message.author)

    def _should_ignore_type(self, message):
        if (message.type is discord.MessageType.pins_add or
            message.type is discord.MessageType.new_member):
            return True
        return False

    def _message_is_ok(self, message):
        text = message.content.strip().lower()

        # Check if starts with 3pseat, 3pfeet, etc
        for keyword in self.message_prefix + self.whitelist_prefix:
            if text.startswith(keyword):
                return True
        # Check if custom emoji
        if re.match(EMOJI_RE, text):
            return True
        # Check if regular emoji
        if text in emoji.UNICODE_EMOJI:
            return True
        # Check if single image
        if text == '' and message.attachments:
            return True
        # Check if single link
        if re.match(URL_RE, text) and len(message.content.split(' ')) == 1:
            return True
        # Check if server message (e.g. when user joins channel announcement)
        if self._should_ignore_type(message):
            return True

        return False

    async def process_server_message(self, message):
        cog = self.get_cog('Memes')
        if cog is not None:
            await cog.troll_reply(message)

        if not self._message_is_ok(message):
            await self.handle_mistake(message)

    async def process_direct_message(self, message):
        await self.send_direct_message(message.author, 'Hi there, I cannot '
                'reply to direct messages.')

    async def on_message(self, message):
        if message.author.bot or self._should_ignore_type(message):
            return
        if message.guild is None:
            await self.process_direct_message(message)
            return
        if not message.content.startswith(self.command_prefix):
            await self.process_server_message(message)
            return
        await self.process_commands(message)

    async def _message_modified(self, message):
        msg = '{}, what did you do to your message? It was: \"{}\"'.format(
              message.author.mention, message.clean_content)
        await self.send_server_message(message.channel, msg)

    async def on_message_delete(self, message):
        if message.author.bot or self._should_ignore_type(message):
            return
        await self._message_modified(message)

    async def on_message_edit(self, before, after):
        if (before.author.bot or after.embeds or 
            self._should_ignore_type(after)):
            return
        # ignore message being edited because it was pinned
        if not before.pinned and after.pinned:
            return
        await self._message_modified(before)

    async def on_ready(self):
        if self.playing_title is not None:
            await self.change_presence(activity=discord.Game(
                                       name=self.playing_title))
        self.logger.info('Logged in as {} (ID={})'.format(self.user.name, self.user.id))

        for ext in EXTENSIONS:
            self.load_extension(ext)
    
    def run(self):
        super().run(self.token, reconnect=True)

