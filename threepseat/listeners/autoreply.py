from __future__ import annotations

import logging
import re

import discord

from threepseat.listeners.listeners import register_listener

logger = logging.getLogger(__name__)


@register_listener('on_message')
async def buh_reply(message: discord.Message) -> None:
    """Replies to messages with buh."""
    if message.author.bot:
        return

    text = message.content.lower()
    if re.search(r'\bbuh\b', text):
        await message.reply(content='3pseat buh')


@register_listener('on_message')
async def pog_reply(message: discord.Message) -> None:
    """Replies to messages with pog (or variations of pog)."""
    if message.author.bot:
        return

    pog_emotes = ['\U0001f1f5', '\U0001f1f4', '\U0001f1ec']
    pog_re = r'(p+\s*)+(o+\s*)+(g+\s*)+'
    pog_emote_re = r'<:.*pog.*:\d*>'

    text = message.content.lower()
    if re.search(pog_re, text) or re.search(pog_emote_re, text):
        msg = await message.reply(content='3pseat poggers')
        for emote in pog_emotes:
            await msg.add_reaction(emote)
