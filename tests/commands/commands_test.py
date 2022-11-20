from __future__ import annotations

import logging
from typing import Any

import discord
import pytest
from discord import app_commands

from testing.mock import MockChannel
from testing.mock import MockClient
from testing.mock import MockInteraction
from testing.mock import MockUser
from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import extract_command_options
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


def test_extract_command_options() -> None:
    interaction = MockInteraction(command=None, user='user')  # type: ignore

    interaction.data = None
    assert extract_command_options(interaction) is None

    interaction.data = {}  # type: ignore
    assert extract_command_options(interaction) is None

    interaction.data = {
        'type': 1,
        'options': [
            {'value': 0, 'type': 4, 'name': 'start'},  # type: ignore
            {'value': 5, 'type': 4, 'name': 'end'},  # type: ignore
        ],
        'name': 'roll',
        'id': '12345',
    }
    expected: dict[str, Any] = {'start': 0, 'end': 5}
    assert extract_command_options(interaction) == expected

    interaction.data = {
        'type': 1,
        'options': [
            {
                'type': 1,
                'options': [
                    {
                        'value': '12345',
                        'type': 6,
                        'name': 'user',
                    },  # type: ignore
                    {
                        'value': True,
                        'type': 2,
                        'name': 'flag',
                    },  # type: ignore
                ],
                'name': 'list',
            },
        ],
        'name': 'rules',
        'id': '997262311901364265',
    }
    expected = {'user': '12345', 'flag': True}
    assert extract_command_options(interaction) == expected


@pytest.mark.asyncio
async def test_log_interaction(caplog) -> None:
    caplog.set_level(logging.INFO)
    interaction = MockInteraction(
        command=None,  # type: ignore
        user=MockUser('user1', 1234),
        channel=MockChannel('channel', 3),
    )
    interaction.data = None
    await log_interaction(interaction)
    assert any(['user1' in record.message for record in caplog.records])
    assert any(['1234' in record.message for record in caplog.records])
