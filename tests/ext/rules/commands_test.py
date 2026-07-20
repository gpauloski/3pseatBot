from __future__ import annotations

import asyncio
import logging
import time
from unittest import mock

import pytest
from discord import app_commands

from testing.asserts import assert_responded
from testing.mock import MockChannel
from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.mock import MockMessage
from testing.mock import MockUser
from testing.utils import extract
from threepseat.ext.rules.commands import RulesCommands
from threepseat.ext.rules.data import GuildConfig
from threepseat.ext.rules.exceptions import EventStartError

GUILD_CONFIG = GuildConfig(
    guild_id=1234,
    enabled=1,
    event_expectancy=0.5,
    event_duration=24,
    event_cooldown=5.0,
    last_event=0,
    max_offenses=3,
    timeout_duration=300,
    prefixes='3pseat, 3pfeet',
)


@pytest.fixture
def commands(tmp_file: str) -> RulesCommands:
    commands = RulesCommands(tmp_file)
    commands.database.update_config(GUILD_CONFIG)
    return commands


async def test_handle_offending_message(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    message = MockMessage('')
    message.author = MockMember('member', 42, guild)
    message.channel = MockChannel('channel')
    message.channel.guild = guild

    with (
        mock.patch.object(message, 'reply', mock.AsyncMock()) as mock_reply,
        mock.patch.object(
            commands,
            'timeout_member',
            mock.AsyncMock(),
        ) as mock_timeout,
    ):
        await commands.handle_offending_message(message)
        await commands.handle_offending_message(message)
        assert mock_reply.await_count == 2

        await commands.handle_offending_message(message)
        assert mock_reply.await_count == 3
        assert mock_timeout.await_count == 1


async def test_timeout_member(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    member = MockMember('member', 42, guild)
    commands.database.add_offense(GUILD_CONFIG.guild_id, 42)

    with mock.patch('discord.Member.timeout') as mock_timeout:
        s = await commands.timeout_member(member, 1)
        assert mock_timeout.await_count == 1
        assert 'timed out' in s

    assert (
        commands.database.get_user(GUILD_CONFIG.guild_id, 42).current_offenses
        == 0
    )

    with mock.patch(
        'discord.Member.timeout',
        mock.AsyncMock(side_effect=Exception()),
    ):
        s = await commands.timeout_member(member, 1)
        assert 'cannot be timed out' in s


async def test_on_message(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    message = MockMessage('3pseat test message')
    message.author = MockMember('member', 42, guild)
    message.channel = MockChannel('channel')
    message.channel.guild = None  # type: ignore[assignment]

    # Most of these calls will be ignored so we use the offending message
    # handler as indication that the message returned without doing anything
    with (
        mock.patch.object(
            commands,
            'handle_offending_message',
            mock.AsyncMock(),
        ) as mock_handler,
        mock.patch(
            'threepseat.ext.rules.commands.ignore_message',
        ) as mock_ignore,
    ):
        # skip because message.channel.guild is None
        await commands.on_message(message)
        assert mock_handler.await_count == 0

        # skip because guild not in event mode
        message.channel.guild = guild
        await commands.on_message(message)
        assert mock_handler.await_count == 0

        commands.event_handlers[GUILD_CONFIG.guild_id] = object()
        # skip because we mock ignore_message to return True
        mock_ignore.return_value = True
        await commands.on_message(message)
        assert mock_handler.await_count == 0
        mock_ignore.return_value = False

        # skip because guild missing config
        with mock.patch.object(
            commands.database,
            'get_config',
            return_value=None,
        ):
            await commands.on_message(message)
        assert mock_handler.await_count == 0

        # skip because message has correct prefix
        await commands.on_message(message)
        assert mock_handler.await_count == 0

        message.content = 'missing prefix'
        await commands.on_message(message)
        assert mock_handler.await_count == 1


async def test_start_event(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with (
        mock.patch.object(commands.database, 'get_config', return_value=None),
        pytest.raises(EventStartError, match='not been configured'),
    ):
        await commands.start_event(guild)

    with (
        mock.patch(
            'threepseat.ext.rules.commands.primary_channel',
            return_value=None,
        ),
        pytest.raises(
            EventStartError,
            match='not find valid text',
        ),
    ):  # pragma: no branch
        await commands.start_event(guild)

    with (
        mock.patch(
            'threepseat.ext.rules.commands.primary_channel',
            return_value=channel,
        ),
        mock.patch.object(channel, 'send', mock.AsyncMock()),
    ):
        await commands.start_event(guild)
        assert guild.id in commands.event_handlers
        handler = commands.event_handlers[guild.id]

        await commands.post_shutdown()
        assert handler.cancelled() or handler.cancelling()
        assert len(commands.event_handlers) == 0


async def test_resume_event(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with (
        mock.patch(
            'threepseat.ext.rules.commands.primary_channel',
            return_value=channel,
        ),
        mock.patch.object(channel, 'send', mock.AsyncMock()) as mock_send,
    ):
        await commands.start_event(guild, resume=True)
        assert guild.id in commands.event_handlers
        commands.event_handlers[guild.id].cancel()
        # Resume should not send event starting message
        assert mock_send.await_count == 0


async def test_stop_event(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with (
        mock.patch(
            'threepseat.ext.rules.commands.primary_channel',
            return_value=channel,
        ),
        mock.patch.object(channel, 'send', mock.AsyncMock()) as mock_send,
    ):
        await commands.start_event(guild)
        await commands.stop_event(guild, channel)
        assert guild.id not in commands.event_handlers
        # Note: twice because of start and stop
        assert mock_send.await_count == 2

        # Calling again should be no-op because there is no longer
        # an active event
        await commands.stop_event(guild, channel)
        assert mock_send.await_count == 2


async def test_stop_event_cancels_stale_task(commands) -> None:
    # Stopping an event must cancel its sleeping task. Otherwise the task
    # wakes after the original duration and ends whatever event is running
    # then, announcing the end of an event that just started.
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with (
        mock.patch(
            'threepseat.ext.rules.commands.primary_channel',
            return_value=channel,
        ),
        mock.patch.object(channel, 'send', mock.AsyncMock()),
    ):
        await commands.start_event(guild)
        first = commands.event_handlers[guild.id]

        await commands.stop_event(guild, channel)
        await asyncio.sleep(0)
        assert first.cancelled() or first.cancelling()

        # A new event is unaffected by the old task.
        await commands.start_event(guild)
        second = commands.event_handlers[guild.id]
        assert second is not first

        await commands.post_shutdown()


async def test_start_event_cancels_overwritten_task(commands) -> None:
    # Starting an event while one is running must not orphan the old task.
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with (
        mock.patch(
            'threepseat.ext.rules.commands.primary_channel',
            return_value=channel,
        ),
        mock.patch.object(channel, 'send', mock.AsyncMock()),
    ):
        await commands.start_event(guild)
        first = commands.event_handlers[guild.id]

        await commands.start_event(guild)
        await asyncio.sleep(0)
        assert first.cancelled() or first.cancelling()
        assert commands.event_handlers[guild.id] is not first

        await commands.post_shutdown()


async def test_event_times_out(commands) -> None:
    # The task created by start_event runs stop_event itself, so stop_event
    # must not cancel the task it is running in before announcing the end.
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with (
        mock.patch(
            'threepseat.ext.rules.commands.primary_channel',
            return_value=channel,
        ),
        mock.patch.object(channel, 'send', mock.AsyncMock()) as mock_send,
    ):
        await commands.start_event(guild, duration=0)
        await commands.event_handlers[guild.id]

    assert guild.id not in commands.event_handlers
    # Once to announce the start, once to announce the end.
    assert mock_send.await_count == 2


async def test_event_starter(commands) -> None:
    client = MockClient(MockUser('bot', 42))
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    starter = commands.event_starter(client)
    func = starter.coro

    with (
        mock.patch.object(commands, 'start_event', mock.AsyncMock()) as mocked,
        mock.patch.object(client, 'get_guild', return_value=guild),
    ):
        with mock.patch('random.random', return_value=1):
            await func()
            assert mocked.await_count == 0

        with mock.patch('random.random', return_value=0):
            await func()
            assert mocked.await_count == 1

        # Test cooldown prevents starting
        config_orig = commands.database.get_config(GUILD_CONFIG.guild_id)
        config_new = config_orig._replace(
            event_cooldown=5,
            event_duration=0,
            last_event=time.time(),
        )
        commands.database.update_config(config_new)
        await func()
        assert mocked.await_count == 1
        # Restore original config
        commands.database.update_config(config_orig)

    with mock.patch.object(client, 'get_guild', return_value=None):
        await func()

    commands.event_handlers[GUILD_CONFIG.guild_id] = object()
    await func()

    commands.database.update_config(GUILD_CONFIG._replace(enabled=0))
    await func()


async def test_configure(commands) -> None:
    configure_ = extract(commands.configure)

    interaction = MockInteraction(
        commands.configure,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    await configure_(commands, interaction, prefixes='3pseat, 3pfeet')
    assert_responded(interaction, 'Update')


async def test_configuration(commands) -> None:
    configuration_ = extract(commands.configuration)

    interaction = MockInteraction(
        commands.configuration,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    await configuration_(commands, interaction)
    assert_responded(interaction, 'Legacy 3pseat mode is')

    interaction = MockInteraction(
        commands.configuration,
        user='user',
        guild=MockGuild('guild', 42),
    )

    await configuration_(commands, interaction)
    assert_responded(interaction, 'has not been configured')


async def test_enable(commands) -> None:
    enable_ = extract(commands.enable)

    interaction = MockInteraction(
        commands.enable,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    with mock.patch.object(commands, 'start_event') as mocked:
        await enable_(commands, interaction, immediate=True)
        assert_responded(interaction, 'Started an event')

        mocked.side_effect = EventStartError()
        await enable_(commands, interaction, immediate=True)
        assert_responded(interaction, 'Failed to start event')

    with mock.patch.object(commands.database, 'get_config', return_value=None):
        await enable_(commands, interaction, immediate=False)
        assert_responded(interaction, 'not been configured')

    await enable_(commands, interaction, immediate=False)
    assert_responded(interaction, '3pseat events are enabled')


async def test_disable(commands) -> None:
    disable_ = extract(commands.disable)

    interaction = MockInteraction(
        commands.disable,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    with (
        mock.patch.object(commands, 'start_event'),
        mock.patch('threepseat.ext.rules.commands.primary_channel'),
    ):
        await disable_(commands, interaction, current=True)
        assert_responded(interaction, 'Stopping any current event')

    with mock.patch.object(commands.database, 'get_config', return_value=None):
        await disable_(commands, interaction)
        assert_responded(interaction, 'not been configured')

    await disable_(commands, interaction)
    assert_responded(interaction, 'events are disabled')


async def test_offenses(commands) -> None:
    offenses_ = extract(commands.offenses)

    interaction = MockInteraction(
        commands.offenses,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )
    member = MockMember('user', 42, MockGuild('guild', GUILD_CONFIG.guild_id))

    with mock.patch.object(commands.database, 'get_config', return_value=None):
        await offenses_(commands, interaction)
        assert_responded(interaction, 'not been configured')

    await offenses_(commands, interaction)
    assert_responded(interaction, 'no offenses yet in this guild')

    commands.database.add_offense(GUILD_CONFIG.guild_id, 42)
    commands.database.add_offense(GUILD_CONFIG.guild_id, 43)
    with mock.patch.object(
        interaction._guild,
        'get_member',
        side_effect=[None, mock.MagicMock()],
    ):
        await offenses_(commands, interaction)
        assert_responded(interaction, 'Current offenses in this')

    await offenses_(commands, interaction, user=member)
    assert_responded(interaction, 'currently has')

    member = MockMember('user', 44, MockGuild('guild', GUILD_CONFIG.guild_id))
    await offenses_(commands, interaction, user=member)
    assert_responded(interaction, 'has not broken the rules')


async def test_add_offense(commands) -> None:
    add_offense_ = extract(commands.add_offense)

    interaction = MockInteraction(
        commands.add_offense,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )
    member = MockMember('user', 42, MockGuild('guild', GUILD_CONFIG.guild_id))

    await add_offense_(commands, interaction, member, count=2)
    assert_responded(interaction, 'Added 2 offenses')

    data = commands.database.get_user(GUILD_CONFIG.guild_id, 42)
    assert data.current_offenses == 2
    commands.database.update_user(data._replace(current_offenses=1000))

    with mock.patch.object(
        commands,
        'timeout_member',
        mock.AsyncMock(return_value='test'),
    ):
        await add_offense_(commands, interaction, member)
    assert_responded(interaction, 'test')

    interaction = MockInteraction(
        commands.add_offense,
        user='user',
        guild=MockGuild('guild', 42),
    )

    await add_offense_(commands, interaction, member)
    assert_responded(interaction, 'not been configured for this guild')


async def test_remove_offenses(commands) -> None:
    remove_offense_ = extract(commands.remove_offense)

    interaction = MockInteraction(
        commands.remove_offense,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )
    member = MockMember('user', 42, MockGuild('guild', GUILD_CONFIG.guild_id))

    await remove_offense_(commands, interaction, member)
    assert_responded(interaction, 'Removed 1 offense')


async def test_reset_offenses(commands) -> None:
    reset_offenses_ = extract(commands.reset_offenses)

    interaction = MockInteraction(
        commands.reset_offenses,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )
    member = MockMember('user', 42, MockGuild('guild', GUILD_CONFIG.guild_id))

    await reset_offenses_(commands, interaction, member)
    assert_responded(interaction, 'Reset offense count')


async def test_on_error(commands, caplog) -> None:
    interaction = MockInteraction(commands.remove_offense, user='user')
    await commands.on_error(
        interaction,
        app_commands.MissingPermissions(['test']),
    )
    message = assert_responded(interaction)
    assert 'test' in message.lower()

    # Should not raise error, just log it
    caplog.set_level(logging.ERROR)
    await commands.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any('test1' in record.message for record in caplog.records)


async def test_resume_events(commands) -> None:
    config = GuildConfig(
        guild_id=100,
        enabled=1,
        event_expectancy=0.5,
        event_duration=60,
        event_cooldown=5.0,
        last_event=time.time(),
        max_offenses=3,
        timeout_duration=300,
        prefixes='3pseat, 3pfeet',
    )
    guild = MockGuild('guild', config.guild_id)
    client = MockClient(MockUser('bot', 42))
    commands.database.update_config(config)

    with (
        mock.patch.object(client, 'get_guild', return_value=guild),
        mock.patch.object(client, 'add_listener'),
        mock.patch.object(
            commands,
            'start_event',
            mock.AsyncMock(),
        ) as mock_start,
    ):
        await commands.post_init(client)
        assert mock_start.await_count == 1
    assert commands._event_starter_task is not None

    await commands.post_shutdown()
    assert commands._event_starter_task is None
    assert commands.database.config_table._db is None

    # Retest with guild not found
    with (
        mock.patch.object(client, 'get_guild', return_value=None),
        mock.patch.object(client, 'add_listener'),
        mock.patch.object(
            commands,
            'start_event',
            mock.AsyncMock(),
        ) as mock_start,
    ):
        await commands.post_init(client)
        assert mock_start.await_count == 0
    await commands.post_shutdown()
