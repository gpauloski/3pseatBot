from __future__ import annotations

import logging

import discord
import pytest
from discord import app_commands

from testing.mock import MockClient
from testing.mock import MockInteraction
from testing.mock import MockUser
from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.commands.commands import registered_app_commands


def test_app_commands_registered() -> None:
    assert len(registered_app_commands()) > 0


@pytest.mark.asyncio
async def test_admin_or_owner() -> None:
    interaction = MockInteraction(
        command=None,  # type: ignore
        user=MockUser('user1', 1234),
    )
    with pytest.raises(app_commands.MissingPermissions):
        await admin_or_owner(interaction)

    interaction = MockInteraction(
        command=None,  # type: ignore
        user=MockUser('user1', 1234),
        client=MockClient(MockUser('user1', 1234)),
    )
    assert await admin_or_owner(interaction)

    class _Perms:
        administrator = True

    class Admin(discord.Member):
        guild_permissions = _Perms()  # type: ignore
        id = 123123132

        def __init__(self) -> None:
            pass

    interaction = MockInteraction(
        command=None,  # type: ignore
        user=Admin(),
    )
    assert await admin_or_owner(interaction)


@pytest.mark.asyncio
async def test_log_interaction(caplog) -> None:
    caplog.set_level(logging.INFO)
    interaction = MockInteraction(
        command=None,  # type: ignore
        user=MockUser('user1', 1234),
    )
    await log_interaction(interaction)
    assert any(['user1' in record.message for record in caplog.records])
    assert any(['1234' in record.message for record in caplog.records])
