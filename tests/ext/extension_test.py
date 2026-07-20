from __future__ import annotations

import logging
from unittest import mock

import pytest
from discord import app_commands

from testing.asserts import assert_responded
from testing.mock import MockInteraction
from threepseat.ext.extension import CommandGroupExtension


@mock.patch('discord.ext.commands.Bot')
async def test_post_init_no_op(mock_bot) -> None:
    ext = CommandGroupExtension()

    await ext.post_init(mock_bot())


async def test_on_error_reports_check_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Check failures are the user's fault (e.g. missing permissions) so the
    # reason is sent back to them rather than swallowed into the log.
    caplog.set_level(logging.INFO)
    ext = CommandGroupExtension()
    interaction = MockInteraction(
        None,  # type: ignore[arg-type]
        user='calling-user',
    )

    await ext.on_error(interaction, app_commands.MissingPermissions(['test']))

    message = assert_responded(interaction)
    assert 'test' in message.lower()
    assert any('check failed' in record.message for record in caplog.records)


async def test_on_error_logs_unexpected_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Anything else is a bug: log it rather than raising out of the command
    # handler, and do not respond with internals.
    caplog.set_level(logging.ERROR)
    ext = CommandGroupExtension()
    interaction = MockInteraction(
        None,  # type: ignore[arg-type]
        user='calling-user',
    )

    await ext.on_error(interaction, app_commands.AppCommandError('test1'))

    assert not interaction.responded
    assert any('test1' in record.message for record in caplog.records)
