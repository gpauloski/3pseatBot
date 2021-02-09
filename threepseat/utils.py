import discord
import emoji
import logging
import os
import re

from discord.ext import commands
from tinydb import TinyDB, Query
from typing import Any, Dict, Optional


logger = logging.getLogger()

URL_RE = (r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.'
          '([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*')
DISCORD_EMOTE_RE = r'<.*:\w*:\d*>'


def is_emoji(text: str) -> bool:
    """Returns True if string is just whitespace and unicode/Discord emojis"""
    # remove unicode emojis from text
    text = emoji.get_emoji_regexp().sub(r'', text)
    # remove discord emojis from text
    text = re.sub(DISCORD_EMOTE_RE, '', text)
    
    # at this point, the string has all emojis removed so if the string
    # is just whitespace then we know it was only emojis
    return text.strip() == ''

def is_admin(member: discord.Member) -> bool:
    """Returns true if guild member is an admin"""
    return member.guild_permissions.administrator

def is_booster(member: discord.Member) -> bool:
    """Returns true is member is a booster for the guild"""
    return member.guild.premium_subscriber_role in member.roles

def is_url(text: str) -> bool:
    """Returns true if text is a single url"""
    return re.match(URL_RE, text) and len(text.split(' ')) == 1

def get_member(user: str, guild: discord.Guild) -> discord.Member:
    """Get Member object from name

    Args:
        name (str): name with format "name#number"
        guild (discord.Guild): guild to get user membership of

    Returns:
        Member
    """
    name = name.split('#')
    return discord.utils.get(
            guild.members, name=name[0], discriminator=name[1])

def log(msg: str, level: str = 'info', 
        context: Optional[commands.Context] = None):
    """Logs message with additional context

    Args:
        msg (str):
        level (str, optional): logging level (default: 'info')
        context (discord.ext.commands.Context, optional): context
            from discord API (default: None)
    """
    prefix = ''
    if context is not None:
        prefix += '[guild={}, channel={}, user={}]'.format(
                context.guild, context.channel, context.author)

    if level == 'info':
        self.logger.info(log_msg)
    elif level == 'warning':
        self.logger.warning(log_msg)
    elif level == 'debug':
        self.logger.debug(log_msg)
    elif level == 'error':
        self.logger.error(log_msg)
    else:
        raise ValueError('Unknown logging level "{}".format(level))')

def keys_to_int(d: Dict[Any, Any]) -> Dict[int, Any]:
    """Converts str keys of dict to int"""
    return {int(k): v for k, v in d.items()}

class Bans:
    def __init__(self, bans_file):
        self.bans_file = bans_file
        if not os.path.exists(os.path.dirname(bans_file)):
            os.makedirs(os.path.dirname(bans_file))
        if not os.path.exists(self.bans_file):
            open(self.bans_file, 'w').close()
        self._db = TinyDB(self.bans_file)
        self._user = Query()

    def get_table(self, guild):
        return self._db.table(guild)

    def get_value(self, guild, name):
        db = self.get_table(guild)
        if not db.search(self._user.name.matches(name)):
            db.insert({'name': name, 'count': 0})
        result = db.search(self._user.name == name)
        user = result.pop(0)
        return user['count']

    def set_value(self, guild, name, value):
        db = self.get_table(guild)
        db.update({'count': value}, self._user.name == name) 

    def add_to_value(self, guild, name, value):
        cur_val = self.get_value(guild, name)
        val = max(0, cur_val + value)
        self.set_value(guild, name, val)
        return val

    def up(self, guild, name):
        val = self.add_to_value(guild, name, 1)
        self.add_to_value(guild, 'server', 1)
        return val
    
    def down(self, guild, name):
        val = self.add_to_value(guild, name, -1)
        self.add_to_value(guild, 'server', -1)
        return val

    def clear(self, guild, name):
        self.set_value(guild, name, 0)
