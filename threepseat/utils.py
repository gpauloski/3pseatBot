import discord
import emoji
import json
import logging
import os
import re

from discord.ext import commands
from typing import Any, Dict, Optional


logger = logging.getLogger()

URL_RE = (r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.'
          '([a-zA-Z]){2,6}([a-zA-Z0-9\.\&\/\?\:@\-_=#])*')
DISCORD_EMOTE_RE = r'<.*:\w*:\d*>'


def is_emoji(text: str) -> bool:
    """Is string whitespace and unicode/Discord emojis

    Args:
        text (str)

    Returns:
        True if `test` is only some combination of unicode emojis,
        Discord emotes, and whitespace.
    """
    text = emoji.get_emoji_regexp().sub(r'', text)  # remove unicode emojis
    text = re.sub(DISCORD_EMOTE_RE, '', text) # remove discord emojis
    # at this point, the string has all emojis removed so if the string
    # is just whitespace then we know it was only emojis
    return text.strip() == ''


def is_admin(member: discord.Member) -> bool:
    """Returns true if guild member is an admin of the guild"""
    return member.guild_permissions.administrator


def is_booster(member: discord.Member) -> bool:
    """Returns true is member is a booster for the guild"""
    return member.guild.premium_subscriber_role in member.roles


def is_url(text: str) -> bool:
    """Returns true if text is a single url"""
    return re.match(URL_RE, text) and len(text.split(' ')) == 1


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


class GuildDatabase:
    """Database abstraction for guild

    'Tables' are created on a per guild basis, indexed by guild ID.
    Each table contains a set of key: values.
    """
    def __init__(self, db_file: str) -> None:
        """
        Args:
            db_file (str): file to save database to
        """
        self.db_file = db_file
        if not os.path.exists(os.path.dirname(self.db_file)):
            os.makedirs(os.path.dirname(self.db_file))
        if os.path.exists(self.db_file):
            with open(self.db_file) as f:
                self.db = keys_to_int(json.load(f))
        else:
            self.db = {}

    def clear(self, guild: discord.Guild, key: str) -> None:
        """Clear value corresponding to key in guild table"""
        tb = self.table(guild)
        if key in tb:
            del tb[key]
        self.save()

    def drop_table(self, guild: discord.Guild) -> None:
        """Drops guild table from database"""
        if guild.id in self.db:
            del db[guild.id]
        self.save()

    def save(self) -> None:
        """Save in memory database to file"""
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=4, sort_keys=True)        

    def set(self, guild: discord.Guild, key: str, value: Any) -> None:
        """Sets value for key in guild table

        Args:
            guild (discord.Guild): guild to get table for
            key (str): key to search table for
            value: any jsonable object
        """
        tb = self.table(guild)
        tb[key] = value
        self.save()

    def table(self, guild: discord.Guild) -> Dict:
        """Get table for guild

        Tables are indexed by guild ID. Makes the table if it does not exist.
        Tables have columns ['key', 'value'].

        Args:
            guild (discord.Guild)

        Returns:
            `dict`
        """
        if guild.id not in self.db:
            self.db[guild.id] = {}
            self.save()
        return self.db[guild.id]

    def value(self, guild: discord.Guild, key: str) -> Optional[Any]:
        """Get value for key in guild table

        Args:
            guild (discord.Guild): guild to get table for
            key (str): key to search table for

        Returns:
            `None` if key does not exist in table else the value for
            `key` in the `guild` table.
        """
        tb = self.table(guild)
        if key in tb:
            return tb[key]
        return None