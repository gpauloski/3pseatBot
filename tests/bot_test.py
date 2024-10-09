from __future__ import annotations

import logging
from unittest import mock

import pytest

from testing.mock import MockGuild
from testing.mock import MockUser
from threepseat.bot import Bot
from threepseat.ext.birthdays import BirthdayCommands
from threepseat.ext.custom import CustomCommands
from threepseat.ext.reminders import ReminderCommands
from threepseat.ext.rules import RulesCommands
from threepseat.ext.sounds import SoundCommands

# NOTE: there is not a great way to mock the discord API/discord Bots right
# now so these tests mock a lot of things. As a result, the quality of these
# tests is severely limited and they shouldn't be fully trusted (but I still
# like to push myself to 100% code coverage).


@pytest.mark.asyncio
async def test_bot_startup(tmp_file: str, caplog) -> None:
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

    assert any(
        ['ready!' in record.message for record in caplog.records],
    )
