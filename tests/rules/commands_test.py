from __future__ import annotations

import logging
from collections.abc import Generator
from unittest import mock

import pytest
from discord import app_commands

from testing.mock import MockChannel
from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockInteraction
from testing.mock import MockMember
from testing.mock import MockMessage
from testing.mock import MockUser
from testing.utils import extract
from threepseat.rules.commands import RulesCommands
from threepseat.rules.data import GuildConfig
from threepseat.rules.exceptions import EventStartError


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
def commands(tmp_file: str) -> Generator[RulesCommands, None, None]:
    commands = RulesCommands(tmp_file)
    commands.database.update_config(GUILD_CONFIG)
    yield commands


@pytest.mark.asyncio
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


@pytest.mark.asyncio
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
    ) as mock_timeout:
        s = await commands.timeout_member(member, 1)
        assert 'cannot be timed out' in s


@pytest.mark.asyncio
async def test_on_message(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    message = MockMessage('3pseat test message')
    message.author = MockMember('member', 42, guild)
    message.channel = MockChannel('channel')
    message.channel.guild = None  # type: ignore

    # Most of these calls will be ignored so we use the offending message
    # handler as indication that the message returned without doing anything
    with (
        mock.patch.object(
            commands,
            'handle_offending_message',
            mock.AsyncMock(),
        ) as mock_handler,
        mock.patch('threepseat.rules.commands.ignore_message') as mock_ignore,
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


@pytest.mark.asyncio
async def test_start_event(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with mock.patch.object(commands.database, 'get_config', return_value=None):
        with pytest.raises(EventStartError, match='not been configured'):
            await commands.start_event(guild)

    with mock.patch(
        'threepseat.rules.commands.primary_channel',
        return_value=None,
    ):
        with pytest.raises(EventStartError, match='not find valid text'):
            await commands.start_event(guild)

    with (
        mock.patch(
            'threepseat.rules.commands.primary_channel',
            return_value=channel,
        ),
        mock.patch.object(channel, 'send', mock.AsyncMock()),
    ):
        await commands.start_event(guild)
        assert guild.id in commands.event_handlers
        commands.event_handlers[guild.id].cancel()


@pytest.mark.asyncio
async def test_stop_event(commands) -> None:
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    channel = MockChannel('channel')

    with (
        mock.patch(
            'threepseat.rules.commands.primary_channel',
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


@pytest.mark.asyncio
async def test_event_starter(commands) -> None:
    client = MockClient(MockUser('bot', 42))
    guild = MockGuild('guild', GUILD_CONFIG.guild_id)
    starter = commands.event_starter(client)
    func = starter.coro

    with (
        mock.patch.object(commands, 'start_event', mock.AsyncMock()) as mocked,
        mock.patch.object(client, 'get_guild', return_value=guild),
    ):
        with mock.patch('random.random', return_value=0):
            await func()
            assert mocked.await_count == 0

        with mock.patch('random.random', return_value=1.1):
            await func()
            assert mocked.await_count == 1

    with mock.patch.object(client, 'get_guild', return_value=None):
        await func()

    commands.event_handlers[GUILD_CONFIG.guild_id] = object()
    await func()

    commands.database.update_config(GUILD_CONFIG._replace(enabled=0))
    await func()


@pytest.mark.asyncio
async def test_configure(commands) -> None:
    configure_ = extract(commands.configure)

    interaction = MockInteraction(
        commands.configure,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    await configure_(commands, interaction, prefixes='3pseat, 3pfeet')
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Update' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_configuration(commands) -> None:
    configuration_ = extract(commands.configuration)

    interaction = MockInteraction(
        commands.configuration,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    await configuration_(commands, interaction)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Legacy 3pseat mode is' in interaction.response_message
    )

    interaction = MockInteraction(
        commands.configuration,
        user='user',
        guild=MockGuild('guild', 42),
    )

    await configuration_(commands, interaction)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'has not been configured' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_enable(commands) -> None:
    enable_ = extract(commands.enable)

    interaction = MockInteraction(
        commands.enable,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    with mock.patch.object(commands, 'start_event') as mocked:
        await enable_(commands, interaction, immediate=True)
        assert interaction.responded
        assert (
            interaction.response_message is not None
            and 'Started an event' in interaction.response_message
        )

        mocked.side_effect = EventStartError()
        await enable_(commands, interaction, immediate=True)
        assert interaction.responded
        assert (
            interaction.response_message is not None
            and 'Failed to start event' in interaction.response_message
        )

    with mock.patch.object(commands.database, 'get_config', return_value=None):
        await enable_(commands, interaction, immediate=False)
        assert interaction.responded
        assert (
            interaction.response_message is not None
            and 'not been configured' in interaction.response_message
        )

    await enable_(commands, interaction, immediate=False)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and '3pseat events are enabled' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_disable(commands) -> None:
    disable_ = extract(commands.disable)

    interaction = MockInteraction(
        commands.disable,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )

    with (
        mock.patch.object(commands, 'start_event'),
        mock.patch('threepseat.rules.commands.primary_channel'),
    ):
        await disable_(commands, interaction, current=True)
        assert interaction.responded
        assert (
            interaction.response_message is not None
            and 'Stopping any current event' in interaction.response_message
        )

    with mock.patch.object(commands.database, 'get_config', return_value=None):
        await disable_(commands, interaction)
        assert interaction.responded
        assert (
            interaction.response_message is not None
            and 'not been configured' in interaction.response_message
        )

    await disable_(commands, interaction)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'events are disabled' in interaction.response_message
    )


@pytest.mark.asyncio
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
        assert interaction.responded
        assert (
            interaction.response_message is not None
            and 'not been configured' in interaction.response_message
        )

    await offenses_(commands, interaction)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'no offenses yet in this guild' in interaction.response_message
    )

    commands.database.add_offense(GUILD_CONFIG.guild_id, 42)
    commands.database.add_offense(GUILD_CONFIG.guild_id, 43)
    with mock.patch.object(
        interaction._guild,
        'get_member',
        side_effect=[None, mock.MagicMock()],
    ):
        await offenses_(commands, interaction)
        assert interaction.responded
        assert (
            interaction.response_message is not None
            and 'Current offenses in this' in interaction.response_message
        )

    await offenses_(commands, interaction, user=member)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'currently has' in interaction.response_message
    )

    member = MockMember('user', 44, MockGuild('guild', GUILD_CONFIG.guild_id))
    await offenses_(commands, interaction, user=member)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'has not broken the rules' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_add_offense(commands) -> None:
    add_offense_ = extract(commands.add_offense)

    interaction = MockInteraction(
        commands.add_offense,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )
    member = MockMember('user', 42, MockGuild('guild', GUILD_CONFIG.guild_id))

    await add_offense_(commands, interaction, member)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Added an offense' in interaction.response_message
    )

    data = commands.database.get_user(GUILD_CONFIG.guild_id, 42)
    commands.database.update_user(data._replace(current_offenses=1000))

    with mock.patch.object(
        commands,
        'timeout_member',
        mock.AsyncMock(return_value='test'),
    ):
        await add_offense_(commands, interaction, member)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'test' in interaction.response_message
    )

    interaction = MockInteraction(
        commands.add_offense,
        user='user',
        guild=MockGuild('guild', 42),
    )

    await add_offense_(commands, interaction, member)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'not been configured for this guild'
        in interaction.response_message
    )


@pytest.mark.asyncio
async def test_remove_offenses(commands) -> None:
    remove_offense_ = extract(commands.remove_offense)

    interaction = MockInteraction(
        commands.remove_offense,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )
    member = MockMember('user', 42, MockGuild('guild', GUILD_CONFIG.guild_id))

    await remove_offense_(commands, interaction, member)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Removed offense' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_reset_offenses(commands) -> None:
    reset_offenses_ = extract(commands.reset_offenses)

    interaction = MockInteraction(
        commands.reset_offenses,
        user='user',
        guild=MockGuild('guild', GUILD_CONFIG.guild_id),
    )
    member = MockMember('user', 42, MockGuild('guild', GUILD_CONFIG.guild_id))

    await reset_offenses_(commands, interaction, member)
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'Reset offense count' in interaction.response_message
    )


@pytest.mark.asyncio
async def test_on_error(commands, caplog) -> None:
    interaction = MockInteraction(commands.remove_offense, user='user')
    await commands.on_error(
        interaction,
        app_commands.MissingPermissions(['test']),
    )
    assert interaction.responded
    assert (
        interaction.response_message is not None
        and 'test' in interaction.response_message.lower()
    )

    # Should not raise error, just log it
    caplog.set_level(logging.ERROR)
    await commands.on_error(interaction, app_commands.AppCommandError('test1'))
    assert any(['test1' in record.message for record in caplog.records])
