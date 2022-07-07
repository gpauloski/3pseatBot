from __future__ import annotations

import discord
import pytest
from discord import app_commands

from testing.mock import MockClient
from testing.mock import MockInteraction
from testing.mock import MockUser
from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import registered_commands


def test_commands_registered() -> None:
    assert len(registered_commands()) > 0


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
