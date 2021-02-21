from threepseat.cogs.commands import Commands
from threepseat.cogs.games import Games
from threepseat.cogs.general import General
from threepseat.cogs.memes import Memes
from threepseat.cogs.minecraft import Minecraft
from threepseat.cogs.poll import Poll
from threepseat.cogs.rules import Rules
from threepseat.cogs.voice import Voice


EXTENSIONS = {
	'commands': Commands,
	'games': Games,
	'general': General,
	'memes': Memes,
	'minecraft': Minecraft,
	'poll': Poll,
	'rules': Rules,
	'voice': Voice
}
"""Maps extension names to the classes"""

__all__ = [
	'EXTENSIONS',
	'Commands',
	'Games',
	'General',
	'Memes',
    'Minecraft',
    'Poll',
    'Rules',
    'Voice'
]