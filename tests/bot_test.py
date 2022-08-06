from __future__ import annotations

import logging
from unittest import mock

import pytest

from testing.mock import MockGuild
from testing.mock import MockUser
from threepseat.birthdays.commands import BirthdayCommands
from threepseat.bot import Bot
from threepseat.commands.custom import CustomCommands
from threepseat.reminders.commands import ReminderCommands
from threepseat.rules.commands import RulesCommands
from threepseat.sounds.commands import SoundCommands

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
        ),
        mock.patch(
            'threepseat.bot.Bot.change_presence',
            mock.AsyncMock(),
        ),
        mock.patch(
            'discord.app_commands.tree.CommandTree.sync',
            mock.AsyncMock(),
        ),
    ):
        bot = Bot(playing_title='3pseat Test Simulator')
        await bot.on_ready()
        assert bot.wait_until_ready.called
        assert bot.change_presence.called
        assert bot.tree.sync.called

        with mock.patch(
            'threepseat.bot.Bot.guilds',
            new_callable=mock.PropertyMock(
                return_value=[MockGuild('guild', 1234)],
            ),
        ):
            bot = Bot(
                birthday_commands=BirthdayCommands(tmp_file),
                custom_commands=CustomCommands(tmp_file),
                sound_commands=SoundCommands(
                    tmp_file,
                    data_path='/tmp/threepseat-test',
                ),
                rules_commands=RulesCommands(tmp_file),
                reminder_commands=ReminderCommands(tmp_file),
            )
            await bot.on_ready()

    assert any(
        ['ready!' in record.message for record in caplog.records],
    )
