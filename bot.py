import configparser
import logging
import json
import inspect
import os
import re

import discord
import emoji

from utils import Bans
from discord.ext import	commands
from dotenv import load_dotenv

# TODO
# - fix url being allowed
# - create 3pseatBans.json if it does not exist
# - add minecraft command be configuarble
# - config json that knows master player
# - games to play
# - Meme of the day command

EMOJI_RE = r'<:\w*:\d*>'
URL_RE = (r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.'
          '([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*')

class Bot(commands.AutoShardedBot):
    def __init__(self, config):
        self.command_prefix = "?"
        self.message_prefix = ["3pseat"]
        self.whitelist_prefix = ["!"]
        self.whitelist_guilds = []
        self.max_offenses = 3
        self.admins = []
        self.playing_title = None
        self.logger = logging.getLogger()

        self._parse_config(config)

        try:
            load_dotenv()
        except Exception as e:
            self.logger.warning("Error loading '.env' file.\n"
                                "{}\n".format(e))

        self.token = os.getenv("TOKEN")

        self.db = Bans()

        super().__init__(command_prefix=self.command_prefix)

    def _parse_config(self, config_file):
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(config_file)
        self.command_prefix = config.get("Default", "command_prefix")
        self.message_prefix = json.loads(config.get("Default", "message_prefix"))
        self.whitelist_prefix = json.loads(config.get("Default", "whitelist_prefix"))
        self.whitelist_guilds = json.loads(config.get("Default", "whitelist_guilds"))
        self.max_offenses = config.getint("Default", "max_offenses")
        self.admins = json.loads(config.get("Default", "admins"))
        self.playing_title = config.get("Default", "playing_title")

    def log(self, log_msg, level="info", guild_name=None):
        if guild_name is not None:
            log_msg = guild_name + ": " + log_msg
        if level == "info":
            self.logger.info(log_msg)
        elif level == "warning":
            self.logger.warning(log_msg)
        elif level == "debug":
            self.logger.debug(log_msg)
        elif level == "error":
            self.logger.error(log_msg)
        else:
            self.logger.error("Unknown logging level \'{}\'".format(level))

    def _should_ignore_type(self, message):
        if (message.type is discord.MessageType.pins_add or
            message.type is discord.MessageType.new_member):
            return True
        return False

    def _should_not_process(self, message):
        text = message.content.strip()

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
        if re.match(URL_RE, text):
            return True
        if self._should_ignore_type(message):
            return True

        return False

    async def _troll_reply(self, message):
        text = message.content.lower()
        regex = r'(i\'?m)|(i am)'
        if re.search(regex, text):
            tokens = text.split(' ')
            keyword = None
            for i, t in enumerate(tokens):
                if re.search(regex, t) and i < len(tokens) - 1:
                    keyword = tokens[i + 1]
            if keyword is None:
                return
            await self.send_message(message.channel, 'Hi {}, I\'m {}!'.format(
                                    keyword, self.user.mention))

    async def send_message(self, channel, message, react_emoji=None):
        msg = self.message_prefix[0] + " " + message
        msg = await channel.send(msg)
        if react_emoji is not None:
            await msg.add_reaction(react_emoji)
        return msg

    async def process_message(self, message):
        await self._troll_reply(message)

        if self._should_not_process(message):
            return

        count = self.db.up(message.guild.name, message.author.name)
        if count >= self.max_offenses:
            self.db.clear(message.guild.name, message.author.name)
            msg = 'I\'m sorry {}, your time as come. RIP.'.format(
                  message.author.mention)
            await self.send_message(message.channel, msg)
            if message.author.guild_permissions.administrator:
                msg = ('Failed to kick {}. Your cognizance is highly '
                       'acknowledged.'.format(message.author.mention))
                await self.send_message(message.channel, msg,
                                        react_emoji='\U0001F9E0')
            else:
                await message.guild.kick(message.author)
                msg = 'Press F to pay respects.'
                await self.send_message(message.channel, msg, 
                                        react_emoji='\U0001F1EB')
            self.log(message.author.name + ' made a fatal mistake',
                     guild_name=message.guild.name)
        else:
            msg = '{}! You\'ve disturbed the spirits'.format(
                  message.author.mention)
            msg = msg + ' ('+ str(count) + '/' + str(self.max_offenses) + ')'
            await self.send_message(message.channel, msg)
            self.log(message.author.name + ' made a mistake (' + 
                     str(count) + '/' + str(self.max_offenses) + ')',
                     guild_name=message.guild.name)

    async def on_message(self, message):
        if message.author.bot or self._should_ignore_type(message):
            return
        if not message.content.startswith(self.command_prefix):
            await self.process_message(message)
            return
        await self.process_commands(message)

    async def _message_modified(self, message):
        msg = '{}, what did you do to your message? It was: \"{}\"'.format(
              message.author.mention, message.clean_content)
        await self.send_message(message.channel, msg)
        self.log(message.author.name + ' modified their message',
                 guild_name=message.guild.name)

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

        self.load_extension("bot_extension")
    
    def run(self):
        super().run(self.token, reconnect=True)
