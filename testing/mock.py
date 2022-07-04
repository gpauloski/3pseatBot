from __future__ import annotations

from typing import Any
from typing import cast

import discord
from discord.app_commands.commands import Command
from discord.interactions import Interaction
from discord.interactions import InteractionResponse


class MockUser(discord.User):
    def __init__(self, name: str, id_: int) -> None:
        self.name = name
        self.id = id_

    @property
    def mention(self) -> str:
        return f'<@{self.name}>'


class MockChannel(discord.TextChannel):
    def __init__(self, name: str) -> None:
        self.name = name


class MockClient(discord.Client):
    def __init__(self, user: discord.User) -> None:
        self._user = user

    @property
    def user(self) -> discord.ClientUser | None:
        return cast(discord.ClientUser, self._user)


class MockGuild(discord.Guild):
    def __init__(self, name: str) -> None:
        self.name = name


class MockMessage(discord.Message):
    def __init__(self, message: str):
        self.clean_content = message


class Response(InteractionResponse):
    def __init__(self) -> None:
        self.called = False
        self.message: str | None = None

    async def send_message(self, message: str) -> None:  # type: ignore
        self.called |= True
        self.message = message


class MockInteraction(Interaction):
    def __init__(
        self,
        command: Command[Any, Any, Any],
        *,
        user: str,
        message: str | None = None,
        channel: str | None = None,
        guild: str | None = None,
    ) -> None:
        self.command = command
        self.user = MockUser(user, 123456789)
        self.message = None if message is None else MockMessage(message)
        self.channel = None if channel is None else MockChannel(channel)
        self._client = MockClient(MockUser('MockBotClient', 31415))
        self._guild = None if guild is None else MockGuild(guild)

        self.response = Response()

    @property
    def client(self) -> discord.Client:
        return self._client

    @property
    def guild(self) -> discord.Guild | None:
        return self._guild

    @property
    def responded(self) -> bool:
        return cast(Response, self.response).called

    @property
    def response_message(self) -> str | None:
        return cast(Response, self.response).message
