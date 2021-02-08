import discord
import emoji
import logging
import re

from discord.ext import commands
from typing import Any, Dict, Optional

from threepseat.constants import DISCORD_EMOTE_RE, URL_RE

logger = logging.getLogger()


def is_emoji(text: str) -> bool:
    """Returns True if string is just whitespace and unicode/Discord emojis"""
    # remove unicode emojis from text
    text = emoji.get_emoji_regexp().sub(r'', text)
    # remove discord emojis from text
    text = re.sub(DISCORD_EMOJI_RE, '', text)
    
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