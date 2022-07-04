from __future__ import annotations

import logging
from unittest import mock

import pytest

from threepseat.bot import Bot

# NOTE: there is not a great way to mock the discord API/discord Bots right
# now so these tests mock a lot of things. As a result, the quality of these
# tests is severely limited and they shouldn't be fully trusted (but I still
# like to push myself to 100% code coverage).


@pytest.mark.asyncio
async def test_bot_startup(bot: Bot, caplog) -> None:
    with mock.patch('discord.ext.commands.Bot.start', mock.AsyncMock()):
        await bot.start()

    # dpytest does not trigger on_ready
    caplog.set_level(logging.INFO)
    with (
        mock.patch.object(
            bot,
            'wait_until_ready',
            mock.AsyncMock(),
        ) as wait_until_ready,
        mock.patch.object(
            bot,
            'change_presence',
            mock.AsyncMock(),
        ) as change_presence,
        mock.patch.object(
            bot.tree,
            'sync',
            mock.AsyncMock(),
        ) as sync,
    ):
        await bot.on_ready()
        assert wait_until_ready.called
        assert change_presence.called
        assert sync.called
    assert any(
        ['ready!' in record.message for record in caplog.records],
    )
