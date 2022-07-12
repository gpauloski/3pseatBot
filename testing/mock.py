from __future__ import annotations

from typing import Any
from typing import cast

import discord
from discord.app_commands.commands import Command
from discord.ext import commands
from discord.interactions import Interaction
from discord.interactions import InteractionResponse


class MockUser(discord.User):
    def __init__(self, name: str, id_: int) -> None:
        self.name = name
        self.id = id_

    @property
    def mention(self) -> str:
        return f'<@{self.name}>'


class MockMember(discord.Member):
    def __init__(self, name: str, id_: int, guild: discord.Guild) -> None:
        self._name = name
        self._id = id_
        self.guild = guild
        self._voice: discord.VoiceState | None = None

    @property
    def name(self) -> str:  # type: ignore
        return self._name

    @property
    def id(self) -> int:  # type: ignore
        return self._id

    @property
    def mention(self) -> str:  # pragma: no cover
        return f'<@{self.name}>'

    @property
    def voice(self) -> discord.VoiceState | None:
        return self._voice


class MockChannel(discord.TextChannel):
    def __init__(self, name: str) -> None:
        self.name = name


class MockVoiceChannel(discord.VoiceChannel):
    def __init__(self) -> None:
        self.name = 'voice-channel'
        self.id = 9876
        self.guild = MockGuild('guild', 4567)

    @property
    def members(self) -> list[discord.Member]:
        return []


class MockClient(commands.Bot):
    def __init__(self, user: discord.User) -> None:
        self._user = user

    @property
    def owner_id(self) -> int:
        return self._user.id

    @property
    def user(self) -> discord.ClientUser | None:
        return cast(discord.ClientUser, self._user)


class MockGuild(discord.Guild):
    def __init__(self, name: str, id: int) -> None:
        self.name = name
        self.id = id
        self._icon = None


class MockMessage(discord.Message):
    def __init__(self, message: str):
        self.clean_content = message


class Response(InteractionResponse):
    def __init__(self) -> None:
        self.called = False
        self.message: str | None = None
        self.deferred = False

    async def send_message(  # type: ignore
        self,
        message: str,
        ephemeral: bool = False,
    ) -> None:
        self.called = True
        self.message = message

    async def defer(self, **kwargs: Any) -> None:
        self.deferred = True


class Followup:
    def __init__(self) -> None:
        self.followed = False
        self.message: str | None = None

    async def send(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.followed = True
        self.message = message


class MockInteraction(Interaction):
    def __init__(
        self,
        command: Command[Any, Any, Any],
        *,
        user: str | discord.User | discord.Member,
        message: str | discord.Message | None = None,
        channel: str | discord.TextChannel | None = None,
        guild: str | discord.Guild | None = None,
        client: discord.Client | None = None,
    ) -> None:
        self.command = command
        self.user = (
            MockUser(user, 123456789) if isinstance(user, str) else user
        )

        if isinstance(message, str):
            message = MockMessage(message)
        self.message: discord.Message | None = message

        if isinstance(channel, str):
            channel = MockChannel(channel)
        self.channel: discord.TextChannel | None = channel  # type: ignore

        if isinstance(guild, str):
            guild = MockGuild(guild, 123982131)
        self._guild = guild

        if client is None:
            client = MockClient(MockUser('MockBotClient', 31415))
        self._client = client

        self.response = Response()
        self.followup = Followup()  # type: ignore

    @property
    def client(self) -> discord.Client:
        return self._client

    @property
    def guild(self) -> discord.Guild | None:
        return self._guild

    @property
    def followed(self) -> bool:
        return (
            self.response.deferred and self.followup.followed  # type: ignore
        )

    @property
    def followup_message(self) -> str | None:
        return self.followup.message  # type: ignore

    @property
    def responded(self) -> bool:
        return cast(Response, self.response).called

    @property
    def response_message(self) -> str | None:
        return cast(Response, self.response).message
