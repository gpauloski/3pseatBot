from __future__ import annotations

from threepseat.listeners.autoreply import buh_reply
from threepseat.listeners.autoreply import pog_reply
from threepseat.listeners.listeners import Listener

# Every listener the bot registers, paired with the event it handles. See
# APP_COMMANDS in threepseat.commands for why these are listed explicitly.
LISTENERS: tuple[Listener, ...] = (
    Listener(buh_reply, 'on_message'),
    Listener(pog_reply, 'on_message'),
)
