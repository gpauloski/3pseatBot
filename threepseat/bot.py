from __future__ import annotations

import logging

import discord
from discord.ext import commands

from threepseat.birthdays.commands import BirthdayCommands
from threepseat.commands.commands import registered_app_commands
from threepseat.commands.custom import CustomCommands
from threepseat.listeners.listeners import registered_listeners
from threepseat.reminders.commands import ReminderCommands
from threepseat.rules.commands import RulesCommands
from threepseat.sounds.commands import SoundCommands
from threepseat.utils import leave_on_empty


logger = logging.getLogger(__name__)


class Bot(commands.Bot):
    """3pseatBot."""

    def __init__(
        self,
        *,
        playing_title: str | None = None,
        birthday_commands: BirthdayCommands | None = None,
        custom_commands: CustomCommands | None = None,
        rules_commands: RulesCommands | None = None,
        sound_commands: SoundCommands | None = None,
        reminder_commands: ReminderCommands | None = None,
    ) -> None:
        """Init Bot.

        Args:
            playing_title (str, optional): set bot as playing this title
                (default: None).
            birthday_commands (BirthdayCommands, optional): birthday commands
                object to register with bot (default: None).
            custom_commands (CustomCommands, optional): custom commands
                object to register with bot (default: None).
            rules_commands (RulesCommands, optional): rules commands
                object to register with bot (default: None).
            sound_commands (SoundCommands, optional): sound commands
                object to register with bot (default: None).
            reminder_commands (ReminderCommands, optional): reminder commands
                object to register with bot (default: None).
        """
        self.playing_title = playing_title
        self.birthday_commands = birthday_commands
        self.custom_commands = custom_commands
        self.rules_commands = rules_commands
        self.sound_commands = sound_commands
        self.reminder_commands = reminder_commands

        intents = discord.Intents(
            guilds=True,
            members=True,
            voice_states=True,
            messages=True,
            message_content=True,
        )

        super().__init__(
            # We are not using command prefixes right now
            command_prefix='???',
            description=None,
            intents=intents,
        )

    async def on_ready(self) -> None:
        """Bot on ready event."""
        await self.setup()
        await self.wait_until_ready()
        logger.info(f'{self.user.name} (Client ID: {self.user.id}) is ready!')

    async def setup(self) -> None:
        """Setup operations to perform once bot is ready."""
        if self.playing_title is not None:
            await self.change_presence(
                activity=discord.Game(name=self.playing_title),
            )

        self.tree.clear_commands(guild=None)
        for guild in self.guilds:
            self.tree.clear_commands(guild=guild)

        commands = registered_app_commands()
        for command in commands:
            self.tree.add_command(command)
        logger.info(f'registered {len(commands)} app commands')

        listeners = registered_listeners()
        for listener in listeners:
            self.add_listener(listener.func, listener.event)
        logger.info(f'registered {len(listeners)} listeners')

        if self.birthday_commands is not None:
            self.tree.add_command(self.birthday_commands)
            self.birthday_checker = self.birthday_commands.birthday_task(self)
            self.birthday_checker.start()
            logger.info('registered birthday command group')

        if self.custom_commands is not None:
            self.tree.add_command(self.custom_commands)
            await self.custom_commands.register_all(self)
            logger.info('registered custom command group')

        if self.rules_commands is not None:
            self.tree.add_command(self.rules_commands)
            self.add_listener(self.rules_commands.on_message, 'on_message')
            self.rule_event_starter = self.rules_commands.event_starter(self)
            self.rule_event_starter.start()
            logger.info('registered rules command group')

        if self.sound_commands is not None:
            self.tree.add_command(self.sound_commands)
            self.voice_channel_checker = leave_on_empty(self, 60)
            self.voice_channel_checker.start()
            logger.info('registered sound command group')

        if self.reminder_commands is not None:
            self.tree.add_command(self.reminder_commands)
            self.reminder_commands.start_repeating_reminders(self)
            logger.info('registered reminders command group')

        await self.tree.sync()
        for guild in self.guilds:
            await self.tree.sync(guild=guild)
