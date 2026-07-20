from __future__ import annotations

from threepseat.commands.commands import Command
from threepseat.commands.emote import emote
from threepseat.commands.general import flip
from threepseat.commands.general import roll
from threepseat.commands.general import source
from threepseat.commands.tts import tts

# Every app command the bot registers. Listed explicitly rather than
# collected by an import-time decorator so the set is greppable and does not
# depend on which modules happen to have been imported.
APP_COMMANDS: tuple[Command, ...] = (
    emote,
    flip,
    roll,
    source,
    tts,
)
