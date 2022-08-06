from __future__ import annotations

from unittest import mock

import pytest

from threepseat.ext.extension import CommandGroupExtension


@pytest.mark.asyncio
@mock.patch('discord.ext.commands.Bot')
async def test_post_init_no_op(mock_bot) -> None:
    ext = CommandGroupExtension()

    await ext.post_init(mock_bot())
