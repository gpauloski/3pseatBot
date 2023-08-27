from __future__ import annotations

import re

import discord
import emoji

URL_RE = (
    r'((http|https)\:\/\/)?[a-zA-Z0-9\.\/\?\:@\-_=#]+\.'
    '([a-zA-Z]){2,6}([a-zA-Z0-9\\.\\&\\/\\?\\:@\\-_=#])*'
)
DISCORD_EMOTE_RE = r'(<a?):\w+:(\d*>)'


def is_emoji(text: str) -> bool:
    """Is string whitespace and unicode/Discord emojis.

    Args:
        text (str): text to check

    Returns:
        True if `text` is only some combination of unicode emojis,
        Discord emotes, and whitespace. Note there must be at least
        one emoji present.
    """
    if text.strip() == '':
        return False
    text = emoji.replace_emoji(text, replace='')
    # unicode emojis are now removed
    text = re.sub(DISCORD_EMOTE_RE, '', text)
    # Discord emojis are now removed so we can just check to see
    # if whitespace is left
    return text.strip() == ''


def is_booster(member: discord.Member) -> bool:
    """Returns true is member is a booster for the guild."""
    return member.guild.premium_subscriber_role in member.roles


def is_url(text: str) -> bool:
    """Returns true if text is a single url."""
    return bool(re.match(URL_RE, text)) and len(text.split(' ')) == 1


def ignore_message(message: discord.Message) -> bool:
    """Determine if message should be ignored by rules enforcement.

    A message will be ignored if it:
      * is not a default message type (e.g., not a pin, game invite, etc.)
      * was sent by a bot
      * was sent by a booster
      * is emojis only
      * is just a url
      * only contains attachments and no text
      * is a quoted message
      * is a code block

    Args:
        message (discord.Message): message to check.

    Returns:
        True if any of the above conditions are met otherwise False.
    """
    if message.type not in (
        discord.MessageType.default,
        discord.MessageType.reply,
    ):
        return True
    if message.author.bot:
        return True
    if isinstance(message.author, discord.Member) and is_booster(
        message.author,
    ):
        return True

    text = message.content.strip().lower()
    if is_emoji(text):
        return True
    if is_url(text):
        return True
    if len(text) == 0 and len(message.attachments) > 0:
        return True
    if text.startswith('> '):
        return True
    if text.startswith('```'):
        return True

    return False
