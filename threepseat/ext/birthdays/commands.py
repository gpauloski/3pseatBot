from __future__ import annotations

import asyncio
import datetime
import enum
import logging
import time

import discord
from discord import app_commands
from discord.ext import tasks

from threepseat.commands.commands import log_interaction
from threepseat.ext.birthdays.data import Birthday
from threepseat.ext.birthdays.data import BirthdayTable
from threepseat.ext.extension import CommandGroupExtension
from threepseat.utils import LoopType
from threepseat.utils import primary_channel

logger = logging.getLogger(__name__)

# Check birthdays at 9am
BIRTHDAY_CHECK_HOUR = 9
BIRTHDAY_CHECK_MINUTE = 0


class Months(enum.Enum):
    """Months enum for command options."""

    January = 1
    February = 2
    March = 3
    April = 4
    May = 5
    June = 6
    July = 7
    August = 8
    September = 9
    October = 10
    November = 11
    December = 12


class BirthdayCommands(CommandGroupExtension):
    """App commands group for birthday messages."""

    def __init__(self, db_path: str) -> None:
        """Init BirthdayCommands.

        Args:
            db_path (str): path to database to use.
        """
        self.table = BirthdayTable(db_path)

        super().__init__(
            name='birthdays',
            description='Guild member birthday messages',
            guild_only=True,
        )

    async def post_init(self, bot: discord.ext.commands.Bot) -> None:
        """Launch birthday task."""
        self._birthday_task = self.birthday_task(bot)
        self._birthday_task.start()
        logger.info('spawning birthday checker background task')

    def birthday_task(self, client: discord.Client) -> LoopType:
        """Return async task that will check for birthdays once per day."""

        @tasks.loop(hours=24)
        async def _checker() -> None:
            logger.info('starting daily birthday check...')
            for guild in client.guilds:
                await self.send_birthday_messages(guild)
            logger.info('finished daily birthday check')

        @_checker.before_loop
        async def _wait_until_start() -> None:
            # source: https://stackoverflow.com/questions/51530012
            now = datetime.datetime.now()
            future = datetime.datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=BIRTHDAY_CHECK_HOUR,
                minute=BIRTHDAY_CHECK_MINUTE,
            )
            # the day offset is 0 if today's check time has not occurred yet or
            # 1 if it is later than the check time (i.e., we need to sleep
            # until tomorrow).
            day_offset = int(
                now.hour >= BIRTHDAY_CHECK_MINUTE
                and now.minute >= BIRTHDAY_CHECK_MINUTE,
            )
            future += datetime.timedelta(days=day_offset)
            await asyncio.sleep((future - now).seconds)

        return _checker

    async def send_birthday_messages(self, guild: discord.Guild) -> None:
        """Checks birthdays in guild and sends messages if they are today."""
        month = datetime.datetime.now().month
        day = datetime.datetime.now().day

        channel = primary_channel(guild)
        if channel is None:
            return

        for birthday in self.table.all(guild.id):
            if birthday.birth_day == day and birthday.birth_month == month:
                member = guild.get_member(birthday.user_id)
                if member is not None:
                    await channel.send(f'Happy Birthday, {member.mention}!')

    @app_commands.command(name='add', description='Add a member birthday')
    @app_commands.describe(
        member='Member the birthday is for',
        month='Month of the member\'s birthday',
        day='Day of the month of the member\'s birthday',
    )
    @app_commands.check(log_interaction)
    async def add(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        month: Months,
        day: app_commands.Range[int, 1, 31],
    ) -> None:
        """Add a birthday for the member of the guild."""
        assert interaction.guild is not None

        try:
            # Use leap year as year
            datetime.datetime(year=2020, month=month.value, day=day)
        except ValueError as e:
            await interaction.response.send_message(
                f'Invalid birthday: {e}.',
                ephemeral=True,
            )
            return

        birthday = Birthday(
            guild_id=interaction.guild.id,
            user_id=member.id,
            author_id=interaction.user.id,
            creation_time=int(time.time()),
            birth_day=day,
            birth_month=month.value,
        )

        self.table.update(birthday)

        await interaction.response.send_message(
            f'Added birthday for {member.mention}.',
            ephemeral=True,
        )

    @app_commands.command(
        name='list',
        description='List birthdays in the guild',
    )
    @app_commands.check(log_interaction)
    async def list(self, interaction: discord.Interaction) -> None:
        """List birthdays in the guild."""
        assert interaction.guild is not None

        birthdays = self.table.all(interaction.guild.id)

        if len(birthdays) == 0:
            await interaction.response.send_message(
                'There are no birthdays in this guild yet.',
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        birthdays.sort(key=lambda b: (b.birth_month, b.birth_day))
        birthdays_strs: list[str] = []
        for birthday in birthdays:
            member = interaction.guild.get_member(birthday.user_id)
            month = Months(birthday.birth_month).name
            day = birthday.birth_day
            if member is not None:
                birthdays_strs.append(f'{member.mention}: {month} {day}')

        await interaction.followup.send('\n'.join(birthdays_strs))

    @app_commands.command(name='remove', description='Remove a birthday')
    @app_commands.describe(member='Member to remove birthday for')
    @app_commands.check(log_interaction)
    async def remove(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ) -> None:
        """Remove a birthday from the guild."""
        assert interaction.guild is not None

        if self.table.get(interaction.guild.id, member.id) is None:
            await interaction.response.send_message(
                f'A birthday has not been added for {member.mention}.',
                ephemeral=True,
            )
            return

        self.table.remove(interaction.guild.id, member.id)
        await interaction.response.send_message(
            f'Removed birthday for {member.mention}.',
            ephemeral=True,
        )
