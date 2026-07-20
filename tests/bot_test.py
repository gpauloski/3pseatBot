from __future__ import annotations

import logging
from unittest import mock

import pytest

from testing.mock import MockGuild
from testing.mock import MockUser
from threepseat.bot import Bot
from threepseat.ext.birthdays import BirthdayCommands
from threepseat.ext.custom import CustomCommands
from threepseat.ext.games import GamesCommands
from threepseat.ext.reminders import ReminderCommands
from threepseat.ext.rules import RulesCommands
from threepseat.ext.sounds import SoundCommands

# NOTE: there is not a great way to mock the discord API/discord Bots right
# now so these tests mock a lot of things. As a result, the quality of these
# tests is severely limited and they shouldn't be fully trusted (but I still
# like to push myself to 100% code coverage).


async def test_bot_startup(
    tmp_file: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    with (
        mock.patch(
            'threepseat.bot.Bot.user',
            new_callable=mock.PropertyMock(
                return_value=MockUser('botuser', 1234),
            ),
        ),
        mock.patch(
            'threepseat.bot.Bot.wait_until_ready',
            mock.AsyncMock(),
        ) as mock_wait_until_ready,
        mock.patch(
            'threepseat.bot.Bot.change_presence',
            mock.AsyncMock(),
        ) as mock_change_presence,
        mock.patch(
            'discord.app_commands.tree.CommandTree.sync',
            mock.AsyncMock(),
        ) as mock_sync,
    ):
        bot = Bot(playing_title='3pseat Test Simulator')
        await bot.on_ready()
        assert mock_wait_until_ready.called
        assert mock_change_presence.called
        assert mock_sync.called

        extensions = [
            BirthdayCommands(tmp_file),
            CustomCommands(tmp_file),
            ReminderCommands(tmp_file),
            RulesCommands(tmp_file),
            SoundCommands(
                tmp_file,
                data_path='/tmp/threepseat-test',
            ),
        ]

        with mock.patch(
            'threepseat.bot.Bot.guilds',
            new_callable=mock.PropertyMock(
                return_value=[MockGuild('guild', 1234)],
            ),
        ):  # pragma: no branch
            bot = Bot(extensions=extensions)
            await bot.on_ready()

    assert any('ready!' in record.message for record in caplog.records)


async def test_bot_setup_runs_once(tmp_file: str) -> None:
    # on_ready fires again on every reconnect. Repeating setup would add a
    # second copy of every listener, restart each extension's background
    # tasks, and re-sync the command tree, which Discord rate limits hard.
    extension = BirthdayCommands(tmp_file)

    with (
        mock.patch(
            'threepseat.bot.Bot.user',
            new_callable=mock.PropertyMock(
                return_value=MockUser('botuser', 1234),
            ),
        ),
        mock.patch('threepseat.bot.Bot.wait_until_ready', mock.AsyncMock()),
        mock.patch('threepseat.bot.Bot.change_presence', mock.AsyncMock()),
        mock.patch(
            'discord.app_commands.tree.CommandTree.sync',
            mock.AsyncMock(),
        ) as mock_sync,
        mock.patch.object(extension, 'post_init', mock.AsyncMock()) as init,
    ):
        bot = Bot(extensions=[extension])
        await bot.on_ready()
        sync_count = mock_sync.await_count

        await bot.on_ready()

    assert init.await_count == 1
    assert mock_sync.await_count == sync_count


async def test_bot_startup_isolates_failures(
    tmp_file: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    bad = GamesCommands(tmp_file)
    good = BirthdayCommands(tmp_file)

    with (
        mock.patch.object(
            bad,
            'post_init',
            mock.AsyncMock(side_effect=RuntimeError('boom')),
        ),
        mock.patch(
            'discord.app_commands.tree.CommandTree.sync',
            mock.AsyncMock(),
        ),
        mock.patch(
            'threepseat.bot.Bot.change_presence',
            mock.AsyncMock(),
        ),
    ):
        bot = Bot(extensions=[bad, good])
        await bot.setup()

    # A failing extension is logged but does not stop the others from
    # registering.
    assert any('post_init failed' in r.message for r in caplog.records)
    assert any(
        'registered birthdays command group' in r.message
        for r in caplog.records
    )


async def test_bot_shutdown_closes_extensions(tmp_file: str) -> None:
    birthdays = BirthdayCommands(tmp_file)
    custom = CustomCommands(tmp_file)
    reminders = ReminderCommands(tmp_file)
    rules = RulesCommands(tmp_file)
    sounds = SoundCommands(tmp_file, data_path='/tmp/threepseat-test')
    bot = Bot(
        extensions=[birthdays, custom, reminders, rules, sounds],
    )

    with mock.patch(
        'discord.ext.commands.Bot.close',
        mock.AsyncMock(),
    ) as mock_close:
        await bot.close()

    assert mock_close.called
    assert birthdays.table._db is None
    assert custom.table._db is None
    assert reminders.table._db is None
    assert rules.database.config_table._db is None
    assert rules.database.offenses_table._db is None
    assert sounds.table._db is None
    assert sounds.join_table._db is None


async def test_bot_shutdown_without_extensions() -> None:
    bot = Bot()

    with mock.patch(
        'discord.ext.commands.Bot.close',
        mock.AsyncMock(),
    ) as mock_close:
        await bot.close()

    assert mock_close.called


async def test_bot_shutdown_isolates_failures(
    tmp_file: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.ERROR)
    bad = GamesCommands(tmp_file)
    good = BirthdayCommands(tmp_file)
    bot = Bot(extensions=[bad, good])

    with (
        mock.patch.object(
            bad,
            'post_shutdown',
            mock.AsyncMock(side_effect=RuntimeError('boom')),
        ),
        mock.patch('discord.ext.commands.Bot.close', mock.AsyncMock()),
    ):
        await bot.close()

    # A failing extension is logged but does not stop the others.
    assert any('post_shutdown failed' in r.message for r in caplog.records)
    assert good.table._db is None
