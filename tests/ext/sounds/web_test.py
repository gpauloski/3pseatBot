from __future__ import annotations

import io
import pathlib
from collections.abc import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
import quart
from quart.datastructures import FileStorage

from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockUser
from threepseat.bot import Bot
from threepseat.ext.sounds.data import MAX_SOUND_FILE_SIZE_BYTES
from threepseat.ext.sounds.data import Sound
from threepseat.ext.sounds.data import SoundsTable
from threepseat.ext.sounds.web import create_app
from threepseat.ext.sounds.web import get_member
from threepseat.ext.sounds.web import get_mutual_guilds
from threepseat.ext.sounds.web import request_too_large


def _upload_file(
    content: bytes = b'fake mp3 data',
    filename: str = 'test.mp3',
) -> FileStorage:
    return FileStorage(stream=io.BytesIO(content), filename=filename)


@pytest_asyncio.fixture
async def quart_app(
    tmp_file: str,
    tmp_path: pathlib.Path,
) -> AsyncGenerator[quart.typing.TestAppProtocol, None]:
    """Generate Quart test app."""
    data_path = str(tmp_path / 'sounds')
    sounds = SoundsTable(db_path=tmp_file, data_path=data_path)

    with (
        mock.patch('threepseat.bot.Bot.user'),
        mock.patch('threepseat.bot.Bot.wait_until_ready'),
        mock.patch('discord.app_commands.tree.CommandTree.sync'),
        mock.patch('quart_discord._http.OAuth2Session'),
        mock.patch('quart_discord.client.DiscordOAuth2Session.fetch_user'),
    ):
        bot = Bot()
        app = create_app(
            bot=bot,
            sounds=sounds,
            client_id=1234,
            client_secret='1234',
            bot_token='1234',
            redirect_uri='http://localhost:5001',
        )

        async with app.test_app() as test_app:  # pragma: no branch
            yield test_app


@pytest.mark.asyncio
async def test_index_authorized(quart_app) -> None:
    # Our test configuration sets authorized by default
    client = quart_app.test_client()

    response = await client.get('/')
    # Redirect to /guilds/
    assert response.status_code == 302
    location = [h for h in response.headers if 'location' in h].pop()
    assert location[1] == '/guilds/'


@pytest.mark.asyncio
async def test_index_unauthorized(quart_app) -> None:
    client = quart_app.test_client()

    # Note: we use mock.AsyncMock(...)() because we are mocking an async
    # property so we want to mock with a coroutine that is awaitable rather
    # than a callable that will return a coroutine
    with mock.patch(
        'quart_discord.client.DiscordOAuth2Session.authorized',
        mock.AsyncMock(return_value=False)(),
    ):
        response = await client.get('/')
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_guilds(quart_app) -> None:
    client = quart_app.test_client()

    with mock.patch(
        'threepseat.ext.sounds.web.get_mutual_guilds',
        return_value=[MockGuild('guild1', 1), MockGuild('guild2', 2)],
    ):
        response = await client.get('/guilds/')

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sound_grid(quart_app) -> None:
    client = quart_app.test_client()

    bot = quart_app.app.config['bot']
    sounds = quart_app.app.config['sounds']

    guild = MockGuild('name', 1)
    sound = Sound(
        uuid='1',
        name='sound1',
        description='a sound',
        link='https://youtube.com',
        author_id=1234,
        guild_id=1234,
        created_time=0,
        filename='',
    )
    sound_list = [sound, sound, sound]

    with (
        mock.patch.object(sounds, 'all', return_value=sound_list),
        mock.patch.object(bot, 'get_guild', return_value=guild),
    ):
        response = await client.get('/sounds/1234')

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sound_play(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']

    with (
        mock.patch.object(sounds, 'get'),
        mock.patch.object(sounds, 'filepath'),
        mock.patch('threepseat.ext.sounds.web.get_member'),
        mock.patch('threepseat.ext.sounds.web.voice_channel'),
        mock.patch('threepseat.ext.sounds.web.play_sound') as mocked,
    ):
        response = await client.post('/play/1234/mysound')
        assert mocked.await_count == 1

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_sound_play_no_member(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch('threepseat.ext.sounds.web.get_member', return_value=None),
        mock.patch('threepseat.ext.sounds.web.play_sound') as mocked,
    ):
        response = await client.post('/play/1234/mysound')
        assert mocked.await_count == 0

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sound_play_no_sound(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']

    with (
        mock.patch.object(sounds, 'get', return_value=None),
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch('threepseat.ext.sounds.web.get_member'),
        mock.patch('threepseat.ext.sounds.web.play_sound') as mocked,
    ):
        response = await client.post('/play/1234/mysound')
        assert mocked.await_count == 0

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sound_play_no_channel(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']

    with (
        mock.patch.object(sounds, 'get'),
        mock.patch.object(sounds, 'filepath'),
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch('threepseat.ext.sounds.web.get_member'),
        mock.patch(
            'threepseat.ext.sounds.web.voice_channel',
            return_value=None,
        ),
        mock.patch('threepseat.ext.sounds.web.play_sound') as mocked,
    ):
        response = await client.post('/play/1234/mysound')
        assert mocked.await_count == 0

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sound_play_error(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']

    with (
        mock.patch.object(sounds, 'get'),
        mock.patch.object(sounds, 'filepath'),
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch('threepseat.ext.sounds.web.get_member'),
        mock.patch('threepseat.ext.sounds.web.voice_channel'),
        mock.patch(
            'threepseat.ext.sounds.web.play_sound',
            mock.AsyncMock(side_effect=Exception()),
        ) as mocked,
    ):
        # Should not raise an error
        response = await client.post('/play/1234/mysound')
        assert mocked.await_count == 1

    assert response.status_code == 400


def test_get_mutual_guilds() -> None:
    client = MockClient(MockUser('name', 1234))

    class _User:
        id = 1234
        username = 'user'

    user = _User()

    with (
        mock.patch.object(client, 'get_user', return_value=None),
        pytest.raises(ValueError, match='Cannot find'),
    ):
        get_mutual_guilds(client, user)

    mock_user = MockUser('name', 1234)

    with (
        mock.patch.object(client, 'get_user', return_value=mock_user),
        mock.patch(
            'discord.User.mutual_guilds',
            new_callable=mock.PropertyMock(return_value=1),
        ),
    ):
        assert get_mutual_guilds(client, user) == 1


def test_get_member() -> None:
    client = MockClient(MockUser('name', 1234))

    class _User:
        id = 1234
        username = 'user'

    user = _User()

    with mock.patch.object(client, 'get_guild', return_value=None):
        assert get_member(client, user, 1234) is None

    guild = MockGuild('name', 1234)

    with (
        mock.patch.object(client, 'get_guild', return_value=guild),
        mock.patch.object(guild, 'get_member', return_value=1),
    ):
        assert get_member(client, user, 1234) == 1


@pytest.mark.asyncio
async def test_sound_add_success(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
        mock.patch(
            'threepseat.ext.sounds.web.mp3_duration_seconds',
            mock.AsyncMock(return_value=1.0),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == 200
    # The sound was actually persisted to the table.
    assert sounds.get('mysound', guild_id=5678) is not None


@pytest.mark.asyncio
async def test_sound_add_no_member(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=None,
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sound_add_no_file(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sound_add_empty_filename(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file(filename='')},
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sound_add_bad_extension(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file(filename='test.txt')},
        )

    assert response.status_code == 400
    assert b'MP3' in await response.get_data()


@pytest.mark.asyncio
async def test_sound_add_bad_description(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': ''},
            files={'file': _upload_file()},
        )

    assert response.status_code == 400
    assert b'Description' in await response.get_data()


@pytest.mark.asyncio
async def test_sound_add_file_too_large(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    # Over the file limit but under MAX_CONTENT_LENGTH so it reaches the
    # handler's explicit size check.
    content = b'x' * (MAX_SOUND_FILE_SIZE_BYTES + 1)

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file(content=content)},
        )

    assert response.status_code == 400
    assert b'File size' in await response.get_data()


@pytest.mark.asyncio
async def test_sound_add_too_long(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
        mock.patch(
            'threepseat.ext.sounds.web.mp3_duration_seconds',
            mock.AsyncMock(return_value=999.0),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == 400
    assert b'too long' in await response.get_data()
    # The partially-written file was cleaned up and nothing was persisted.
    assert sounds.get('mysound', guild_id=5678) is None


@pytest.mark.asyncio
async def test_sound_add_duplicate_name(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    # Pre-existing sound with the same name.
    existing = Sound.new(
        name='mysound',
        description='existing',
        link=None,
        author_id=1234,
        guild_id=5678,
    )
    pathlib.Path(sounds.filepath(existing.filename)).touch()
    sounds.add(existing)

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
        mock.patch(
            'threepseat.ext.sounds.web.mp3_duration_seconds',
            mock.AsyncMock(return_value=1.0),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == 400
    assert b'already exists' in await response.get_data()


@pytest.mark.asyncio
async def test_sound_add_save_error(quart_app) -> None:
    client = quart_app.test_client()

    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=object()),
        ),
        mock.patch(
            'threepseat.ext.sounds.web.get_member',
            return_value=member,
        ),
        mock.patch(
            'threepseat.ext.sounds.web.mp3_duration_seconds',
            mock.AsyncMock(side_effect=RuntimeError('probe failed')),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == 400
    assert b'Failed to save' in await response.get_data()


@pytest.mark.asyncio
async def test_request_too_large_handler() -> None:
    # Uploads exceeding MAX_CONTENT_LENGTH are rejected by the ASGI server
    # with a 413 before reaching the handler; verify the friendly response.
    response = await request_too_large(Exception())
    assert isinstance(response, quart.Response)
    assert response.status_code == 413
    assert b'File size' in await response.get_data()
