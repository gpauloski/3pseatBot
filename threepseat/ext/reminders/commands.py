from __future__ import annotations

import datetime
import logging
import time
from typing import NamedTuple

import discord
from discord import app_commands

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.ext.extension import MAX_CHOICES_LENGTH
from threepseat.ext.extension import CommandGroupExtension
from threepseat.ext.reminders.data import Reminder
from threepseat.ext.reminders.data import RemindersTable
from threepseat.ext.reminders.data import ReminderType
from threepseat.ext.reminders.utils import reminder_task
from threepseat.utils import LoopType
from threepseat.utils import alphanumeric
from threepseat.utils import readable_timedelta

MAX_TEXT_LENGTH = 200
WARN_ON_LONG_DELAY = 6 * 60

logger = logging.getLogger(__name__)


class ReminderTask(NamedTuple):
    """Reminder Task Data."""

    kind: ReminderType
    reminder: Reminder
    task: LoopType


class ReminderTaskKey(NamedTuple):
    """Reminder Task Key."""

    guild_id: int
    name: str


class ReminderCommands(CommandGroupExtension):
    """App commands for reminders for text and voice channels."""

    def __init__(self, db_path: str) -> None:
        """Init ReminderCommands.

        Args:
            db_path (str): path to database to use.
        """
        # The database is just used for storing repeating tasks between
        # bot restarts
        self.table = RemindersTable(db_path)

        # Finished tasks should be removed from this dict
        self._tasks: dict[ReminderTaskKey, ReminderTask] = {}

        super().__init__(
            name='reminders',
            description='Create reminders in text or voice channels',
            guild_only=True,
        )

    async def post_init(self, bot: discord.ext.commands.Bot) -> None:
        """Spawn all saved repeating reminder tasks."""
        for guild in bot.guilds:
            for reminder in self.table.all(guild.id):
                self.start_reminder(bot, reminder, ReminderType.REPEATING)

    def start_reminder(
        self,
        client: discord.Client,
        reminder: Reminder,
        kind: ReminderType,
    ) -> None:
        """Start a new reminder task."""
        key = ReminderTaskKey(reminder.guild_id, reminder.name)
        if key in self._tasks:
            return

        def _remove_callback() -> None:
            self._tasks.pop(key, None)

        task: LoopType = reminder_task(
            client,
            reminder,
            kind,
            _remove_callback if kind == ReminderType.ONE_TIME else None,
        )
        task.start()
        self._tasks[key] = ReminderTask(kind, reminder, task)
        logger.info(
            f'started {kind.value} reminder task {reminder.name} in guild '
            f'{reminder.guild_id} and channel {reminder.channel_id} ',
        )

    def stop_reminder(self, guild_id: int, name: str) -> None:
        """Stop a running reminder task."""
        key = ReminderTaskKey(guild_id, name)
        value = self._tasks.pop(key, None)
        if value is not None:
            value.task.cancel()
            logger.info(
                f'cancelled reminder task {name} in guild {guild_id} '
                f'and channel {value.reminder.channel_id}',
            )

    async def autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Return list of reminders in the guild matching current query."""
        assert interaction.guild is not None
        name_kinds = [
            (key.name, value.kind.value)
            for key, value in self._tasks.items()
            if interaction.guild.id == key.guild_id
        ]
        choices = [
            app_commands.Choice(name=f'{name} ({kind})', value=name)
            for name, kind in name_kinds
            if current.lower() in name.lower() or current == ''
        ]
        choices = sorted(choices, key=lambda c: c.name.lower())
        return choices[: min(len(choices), MAX_CHOICES_LENGTH)]

    @app_commands.command(
        name='create',
        description='[Admin Only] Create a new reminder',
    )
    @app_commands.describe(
        kind='Choose a one-time or repeating reminder',
        name='Name of the reminder (alphanumeric characters only)',
        text=f'Reminder body text (max {MAX_TEXT_LENGTH} character)',
        channel='Channel to send the reminder in',
        delay='Minutes before sending reminder/delay before repeating',
    )
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def create(
        self,
        interaction: discord.Interaction,
        kind: ReminderType,
        name: app_commands.Range[str, 1, 18],
        text: app_commands.Range[str, 1, MAX_TEXT_LENGTH],
        channel: discord.TextChannel | discord.VoiceChannel,
        delay: app_commands.Range[int, 1, None],
    ) -> None:
        """Create a new reminder."""
        assert interaction.guild is not None

        if not alphanumeric(name) or len(name) == 0:
            await interaction.response.send_message(
                'The reminder must be a single word with only '
                'alphanumeric characters.',
                ephemeral=True,
            )
            return

        key = ReminderTaskKey(interaction.guild.id, name)
        if key in self._tasks:
            await interaction.response.send_message(
                f'A reminder named *{name}* already exists.',
                ephemeral=True,
            )
            return

        reminder = Reminder(
            guild_id=interaction.guild.id,
            channel_id=channel.id,
            author_id=interaction.user.id,
            creation_time=int(time.time()),
            name=name,
            text=text,
            delay_minutes=delay,
        )

        if kind == ReminderType.REPEATING:
            self.table.update(reminder)

        self.start_reminder(
            interaction.client,
            reminder,
            kind,
        )

        msg = f'Created {kind.value} reminder named *{name}*.'
        if delay > WARN_ON_LONG_DELAY and kind == ReminderType.ONE_TIME:
            msg = (
                f'{msg} Note that one-time reminders with very long delays '
                'may be lost if the bot restarts. Repeating reminders persist '
                'across bot restarts.'
            )

        await interaction.response.send_message(msg, ephemeral=True)
        logger.info(f'created new reminder: {reminder}')

    @app_commands.command(
        name='info',
        description='Get info about a reminder',
    )
    @app_commands.describe(name='Name of reminder to query')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(log_interaction)
    async def info(self, interaction: discord.Interaction, name: str) -> None:
        """Get info about a reminder."""
        assert interaction.guild is not None

        key = ReminderTaskKey(interaction.guild.id, name)
        if key not in self._tasks:
            await interaction.response.send_message(
                f'A reminder named *{name}* does not exist.',
                ephemeral=True,
            )
            return
        value = self._tasks[key]
        reminder = value.reminder

        user = interaction.client.get_user(reminder.author_id)
        user_str = user.mention if user is not None else 'unknown'
        channel = interaction.guild.get_channel(reminder.channel_id)
        channel_str = channel.mention if channel is not None else 'unknown'
        date = datetime.datetime.fromtimestamp(
            reminder.creation_time,
        ).strftime('%B %d, %Y')
        delay = readable_timedelta(minutes=reminder.delay_minutes)
        msg = (
            f'Reminder *{reminder.name}* ({value.kind.value}):\n'
            f' - message: {reminder.text}\n'
            f' - channel: {channel_str}\n'
            f' - delay: {delay}\n'
            f' - author: {user_str}\n'
            f' - created: {date}\n'
        )

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='list',
        description='List all reminders in the guild',
    )
    @app_commands.check(log_interaction)
    async def list(self, interaction: discord.Interaction) -> None:
        """List reminder in the guild."""
        assert interaction.guild is not None

        reminders = [
            value
            for key, value in self._tasks.items()
            if interaction.guild.id == key.guild_id
        ]
        if len(reminders) == 0:
            await interaction.response.send_message(
                'There are no reminders in this guild yet.',
                ephemeral=True,
            )
            return

        lines = []
        for value in reminders:
            channel = interaction.guild.get_channel(value.reminder.channel_id)
            channel_str = channel.mention if channel is not None else 'unknown'
            lines.append(
                f'{value.reminder.name}: {value.kind.value} reminder in '
                f'{channel_str}',
            )

        lines_str = '\n - '.join(lines)
        msg = f'Exisiting reminders:\n - {lines_str}'

        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(
        name='remove',
        description='[Admin Only] Remove a reminder',
    )
    @app_commands.describe(name='Name of reminder to remove')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def remove(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Remove a reminder."""
        assert interaction.guild is not None

        key = ReminderTaskKey(interaction.guild.id, name)
        if key not in self._tasks:
            await interaction.response.send_message(
                f'A reminder named *{name}* does not exist.',
                ephemeral=True,
            )
            return

        value = self._tasks[key]
        if value.kind == ReminderType.REPEATING:
            self.table.remove(interaction.guild.id, name)

        self.stop_reminder(interaction.guild.id, name)
        await interaction.response.send_message(
            f'Removed the reminder *{name}*.',
            ephemeral=True,
        )
