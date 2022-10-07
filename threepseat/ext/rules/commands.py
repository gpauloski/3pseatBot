from __future__ import annotations

import asyncio
import datetime
import logging
import random
import time

import discord
from discord import app_commands
from discord.ext import tasks

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.ext.extension import CommandGroupExtension
from threepseat.ext.rules.data import GuildConfig
from threepseat.ext.rules.data import RulesDatabase
from threepseat.ext.rules.exceptions import EventStartError
from threepseat.ext.rules.exceptions import GuildNotConfiguredError
from threepseat.ext.rules.exceptions import MaxOffensesExceededError
from threepseat.ext.rules.utils import ignore_message
from threepseat.utils import primary_channel
from threepseat.utils import readable_sequence
from threepseat.utils import readable_timedelta
from threepseat.utils import split_strings

logger = logging.getLogger(__name__)

NOT_CONFIGURED_MESSAGE = (
    'Legacy 3pseat mode has not been configured for this guild. '
    'Use `/rules configure` to get started.'
)


class RulesCommands(CommandGroupExtension):
    """App commands for rules extension."""

    def __init__(self, db_path: str) -> None:
        """Init RulesCommands.

        Args:
            db_path (str): path to database to use.
        """
        self.database = RulesDatabase(db_path=db_path)

        # Mapping of guild IDs to the current task handling the event
        self.event_handlers: dict[int, asyncio.Task[None]] = {}

        super().__init__(
            name='rules',
            description='Enforce legacy 3pseat rules for this channel',
            guild_only=True,
        )

    async def post_init(self, bot: discord.ext.commands.Bot) -> None:
        """Add the message listener to the bot and spawn the event starter."""
        bot.add_listener(self.on_message, 'on_message')
        self._event_starter_task = self.event_starter(bot)
        self._event_starter_task.start()

    async def handle_offending_message(self, message: discord.Message) -> None:
        """Handle side effects for message that breaks rules.

        Adds a strike to the user and either tells them they have broken
        the rules or times them out if they have broken the rules too many
        times.
        """
        assert message.channel.guild is not None
        config = self.database.get_config(guild_id=message.channel.guild.id)
        if config is None:
            raise AssertionError('Unreachable.')

        try:
            current = self.database.add_offense(
                guild_id=message.channel.guild.id,
                user_id=message.author.id,
            )
        except MaxOffensesExceededError:
            assert isinstance(message.author, discord.Member)
            msg = await self.timeout_member(
                message.author,
                config.timeout_duration,
            )
            await message.reply(msg)
        else:
            await message.reply(
                f'3pseat {message.author.mention}! You\'ve disturbed the '
                f'spirits ({current}/{config.max_offenses}).',
            )

    async def timeout_member(
        self,
        member: discord.Member,
        duration: float,
    ) -> str:
        """Attempt to timeout member.

        Resets offenses for the member, attempts to time them out,
        and returns a message that the caller can send with the results.
        """
        logger.info(
            f'timing out {member.name} in {member.guild.name} '
            f'({member.guild.id})',
        )
        self.database.reset_current_offenses(
            guild_id=member.guild.id,
            user_id=member.id,
        )
        try:
            await member.timeout(
                datetime.timedelta(minutes=duration),
                reason='Breaking the rules too many times.',
            )
        except Exception as e:
            logger.exception(
                f'failed to timeout {member.name} in {member.guild.name} '
                f'({member.guild.id}): {e}',
            )
            return (
                f'3pseat {member.mention}! You\'ve disturbed the '
                f'spirits too many times, but you cannot be timed out. '
                'Your cognizance is highly acknowledged.'
            )
        else:
            return (
                f'3pseat {member.mention} has been timed out for {duration} '
                'minutes for disturbing too many spirits.'
            )

    async def on_message(self, message: discord.Message) -> None:
        """Message handler for rules events.

        Check if the message comes from a text channel in a guild
        where rules enforcement is active and verifies if the message
        passes the rules.
        """
        if (
            not isinstance(message.channel, discord.TextChannel)
            or message.channel.guild is None
        ):
            return

        if message.channel.guild.id not in self.event_handlers:
            return

        if ignore_message(message):
            return

        config = self.database.get_config(message.channel.guild.id)
        if config is None:
            logger.error(
                f'rules enabled for guild {message.channel.guild.name} '
                f'({message.channel.guild.id}) but the guild has not been '
                'configured',
            )
            return

        content = message.content.strip().lower()
        for prefix in split_strings(config.prefixes):
            if content.startswith(prefix.lower()):
                return

        await self.handle_offending_message(message)

    async def start_event(
        self,
        guild: discord.Guild,
        duration: float | None = None,
    ) -> None:
        """Start a rules enforcement event for the guild."""
        config = self.database.get_config(guild.id)
        if config is None:
            raise EventStartError(
                f'Guild {guild.name} ({guild.id}) has not been configured.',
            )

        channel = primary_channel(guild)
        if channel is None:
            raise EventStartError(
                'Could not find valid text channel for guild '
                f'{guild.name} ({guild.id})',
            )

        duration = config.event_duration if duration is None else duration
        duration_readable = readable_timedelta(minutes=duration)
        prefixes = readable_sequence(split_strings(config.prefixes), 'or')

        await channel.send(
            f'3pseat mode is starting for {duration_readable}! '
            f'All messages with text must start with {prefixes}.',
        )

        logger.info(
            f'starting rules event for {guild.name} ({guild.id}) for '
            f'{duration}',
        )
        self.event_handlers[guild.id] = asyncio.create_task(
            self.stop_event(
                guild=guild,
                channel=channel,
                sleep_seconds=duration * 60,
            ),
        )

        # Starting event success so update last_event time
        config = config._replace(last_event=time.time())
        self.database.update_config(config)

    async def stop_event(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel | None,
        sleep_seconds: float = 0,
    ) -> None:
        """Stop rules enforcement event for a guild."""
        await asyncio.sleep(sleep_seconds)

        handler = self.event_handlers.pop(guild.id, None)
        if handler is not None and channel is not None:
            logger.info(f'stopping rules event for {guild.name} ({guild.id})')
            await channel.send('3pseat mode has ended.')

    def event_starter(
        self,
        client: discord.Client,
        interval_minutes: float = 60,
    ) -> tasks.Loop[tasks.LF]:
        """Create task that will periodically start events.

        Usage:
            >>> rules = RulesCommands(...)
            >>> event_starter = rules.event_starter(bot)
            >>> event_starter.start()
        """

        @tasks.loop(minutes=interval_minutes)
        async def _event_starter() -> None:
            logger.info('starting periodic rules event starter routine')
            chances_per_day = (60 * 24) / interval_minutes
            for config in self.database.get_configs():
                if not bool(config.enabled):
                    continue
                if config.guild_id in self.event_handlers:
                    continue
                guild = client.get_guild(config.guild_id)
                if guild is None:
                    continue
                # Skip if still in cooldown period
                last_event_delta = time.time() - config.last_event
                if (
                    # Check > 0 in case current time is before last_event
                    0 < last_event_delta < config.event_cooldown * 60
                    and config.last_event > 0
                ):
                    continue
                # Expectancy is expected number of events per day so scale
                # by number of chances for an event to start per day. For
                # example, if event_expectancy is 0.25 (one event every
                # four days) and chances per day is 24, p = 0.25/24.
                # Then we pick a random number is trigger the event if less
                # than p.
                p = max(min(config.event_expectancy / chances_per_day, 1), 0)
                if random.random() <= p:
                    await self.start_event(guild)

        return _event_starter

    @app_commands.command(
        name='configure',
        description=(
            '[Admin Only] Configure legacy 3pseat events for this guild'
        ),
    )
    @app_commands.describe(
        prefixes='Comma-separated list of prefixes',
        expectancy=(
            'Expected number of event occurrences per day '
            '(default: 2/7, twice per week)'
        ),
        cooldown=(
            'Cooldown between random events in minutes (default: 720 minutes)'
        ),
        duration='Duration of event in minutes (default: 60 minutes)',
        max_offenses='Max offenses before user is timed out (default: 3)',
        timeout='Minutes to timeout user for (default: 3 minutes)',
    )
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def configure(
        self,
        interaction: discord.Interaction,
        prefixes: str,
        expectancy: app_commands.Range[float, 0.0, None] = 2 / 7,
        cooldown: app_commands.Range[float, 0.0, None] = 720.0,
        duration: app_commands.Range[float, 1.0, None] = 60.0,
        max_offenses: app_commands.Range[int, 1, None] = 3,
        timeout: app_commands.Range[float, 0.0, None] = 3.0,
    ) -> None:
        """Configure events for a guild."""
        assert interaction.guild is not None

        # This ensures there is one space after each part in case the user
        # has it formatted slightly differently
        prefixes = ', '.join(split_strings(prefixes))

        config = GuildConfig(
            guild_id=interaction.guild.id,
            enabled=False,
            event_expectancy=expectancy,
            event_duration=duration,
            event_cooldown=cooldown,
            last_event=0,
            max_offenses=max_offenses,
            timeout_duration=timeout,
            prefixes=prefixes,
        )
        self.database.update_config(config)
        await interaction.response.send_message(
            'Updated legacy 3pseat event configuration for '
            f'{interaction.guild.name}. Enable the events with '
            '`/rules enable`.',
            ephemeral=True,
        )

    @app_commands.command(
        name='configuration',
        description='View the event configuration for this channel',
    )
    @app_commands.check(log_interaction)
    async def configuration(self, interaction: discord.Interaction) -> None:
        """Check the configuration for the guild."""
        assert interaction.guild is not None
        config = self.database.get_config(guild_id=interaction.guild.id)

        if config is None:
            await interaction.response.send_message(
                NOT_CONFIGURED_MESSAGE,
                ephemeral=True,
            )
            return

        enabled = 'enabled' if config.enabled > 0 else 'disabled'
        last_event = (
            'never'
            if config.last_event == 0
            else datetime.datetime.fromtimestamp(config.last_event).strftime(
                '%-d %B %Y at %-I:%M:%S %p',
            )
        )
        event_duration = readable_timedelta(minutes=config.event_duration)
        timeout_duration = readable_timedelta(minutes=config.timeout_duration)
        prefixes = readable_sequence(split_strings(config.prefixes), 'or')

        await interaction.response.send_message(
            f'Legacy 3pseat mode is **{enabled}**.\n'
            f'- *Expected events per day*: {config.event_expectancy}\n'
            f'- *Event duration*: {event_duration}\n'
            f'- *Max offenses before timeout*: {config.max_offenses}\n'
            f'- *Timeout duration*: {timeout_duration}\n'
            f'- *Prefix pattern*: {prefixes}\n'
            f'- *Last event*: {last_event}',
            ephemeral=True,
        )

    @app_commands.command(
        name='enable',
        description='[Admin Only] Enable legacy 3pseat events for the guild',
    )
    @app_commands.describe(
        immediate='Optionally start event immediately',
        duration='Override duration (minutes) if starting event immediately',
    )
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def enable(
        self,
        interaction: discord.Interaction,
        immediate: bool = False,
        duration: app_commands.Range[float, 1.0, None] | None = None,
    ) -> None:
        """Enable events for the guild."""
        assert interaction.guild is not None
        if immediate:
            try:
                await self.start_event(interaction.guild, duration=duration)
            except EventStartError as e:
                await interaction.response.send_message(
                    f'Failed to start event: {e}.',
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    'Started an event.',
                    ephemeral=True,
                )
        else:
            config = self.database.get_config(guild_id=interaction.guild.id)
            if config is None:
                await interaction.response.send_message(
                    NOT_CONFIGURED_MESSAGE,
                    ephemeral=True,
                )
                return

            self.database.update_config(config._replace(enabled=int(True)))
            await interaction.response.send_message(
                'Legacy 3pseat events are enabled.',
                ephemeral=True,
            )

    @app_commands.command(
        name='disable',
        description='[Admin Only] Disable legacy 3pseat events for the guild',
    )
    @app_commands.describe(current='Optionally only stop the current event')
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def disable(
        self,
        interaction: discord.Interaction,
        current: bool = False,
    ) -> None:
        """Disable events for the guild."""
        assert interaction.guild is not None
        if current:
            await self.stop_event(
                interaction.guild,
                primary_channel(interaction.guild),
            )
            await interaction.response.send_message(
                'Stopping any current event.',
                ephemeral=True,
            )
        else:
            config = self.database.get_config(guild_id=interaction.guild.id)
            if config is None:
                await interaction.response.send_message(
                    NOT_CONFIGURED_MESSAGE,
                    ephemeral=True,
                )
                return

            self.database.update_config(config._replace(enabled=int(False)))
            await interaction.response.send_message(
                'Legacy 3pseat events are disabled.',
                ephemeral=True,
            )

    @app_commands.command(
        name='list',
        description='List offenses for the guild',
    )
    @app_commands.describe(user='If specified, only check a specific user')
    @app_commands.check(log_interaction)
    async def offenses(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        """Check offenses in the guild."""
        assert interaction.guild is not None
        guild_id = interaction.guild.id

        config = self.database.get_config(guild_id=guild_id)
        if config is None:
            await interaction.response.send_message(
                NOT_CONFIGURED_MESSAGE,
                ephemeral=True,
            )
            return

        if user is None:
            users_data = self.database.get_users(guild_id=guild_id)

            if len(users_data) == 0:
                await interaction.response.send_message(
                    'There have been no offenses yet in this guild.',
                )
                return

            users_: list[str] = []
            for data in users_data:
                member = interaction.guild.get_member(data.user_id)
                if member is not None:
                    users_.append(
                        f'{member.display_name}: '
                        f'{data.current_offenses}/{config.max_offenses}',
                    )
            users_.sort()
            users_str = '\n'.join(users_)
            await interaction.response.send_message(
                f'Current offenses in this guild:\n```\n{users_str}\n```',
            )
        else:
            user_data = self.database.get_user(
                guild_id=guild_id,
                user_id=user.id,
            )
            if user_data is None:
                await interaction.response.send_message(
                    f'{user.mention} has not broken the rules yet.',
                )
                return
            last_offense = datetime.datetime.fromtimestamp(
                user_data.last_offense,
            ).strftime('%-d %B %Y at %-I:%M:%S %p')
            await interaction.response.send_message(
                f'{user.mention} currently has {user_data.current_offenses}/'
                f'{config.max_offenses} offenses and '
                f'{user_data.total_offenses} in total. '
                f'Their last offense was on {last_offense}.',
            )

    @app_commands.command(
        name='add',
        description='[Admin Only] Add an offense to the user',
    )
    @app_commands.describe(user='User to add offense to')
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def add_offense(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        """Add an offense to the member."""
        assert interaction.guild is not None
        try:
            current = self.database.add_offense(
                guild_id=interaction.guild.id,
                user_id=user.id,
            )
        except GuildNotConfiguredError:
            await interaction.response.send_message(
                NOT_CONFIGURED_MESSAGE,
                ephemeral=True,
            )
        except MaxOffensesExceededError:
            config = self.database.get_config(interaction.guild.id)
            # Note if config was None, then GuildNotConfiguredError above
            # would be raised.
            assert config is not None
            msg = await self.timeout_member(user, config.timeout_duration)
            await interaction.response.send_message(msg)
        else:
            await interaction.response.send_message(
                f'Added an offense to {user.mention}. '
                f'They now have {current}.',
            )

    @app_commands.command(
        name='remove',
        description='[Admin Only] Remove an offense from the user',
    )
    @app_commands.describe(user='User to remove offense from')
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def remove_offense(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        """Remove an offense from the member."""
        assert interaction.guild is not None
        self.database.remove_offense(interaction.guild.id, user.id)
        await interaction.response.send_message(
            f'Removed offense from {user.mention}.',
        )

    @app_commands.command(
        name='reset',
        description='[Admin Only] Reset a user\'s offense count',
    )
    @app_commands.describe(user='User to reset')
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def reset_offenses(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
    ) -> None:
        """Reset offenses for the member."""
        assert interaction.guild is not None
        self.database.reset_current_offenses(interaction.guild.id, user.id)
        await interaction.response.send_message(
            f'Reset offense count for {user.mention}.',
        )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Callback for errors in child functions."""
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(str(error), ephemeral=True)
            logger.info(f'app command check failed: {error}')
        else:
            logger.exception(error)
