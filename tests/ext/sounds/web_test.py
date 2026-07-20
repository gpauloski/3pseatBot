from __future__ import annotations

import io
import logging
import pathlib
from collections.abc import AsyncGenerator
from http import HTTPStatus
from unittest import mock

import pytest
import quart
from quart.datastructures import FileStorage

from testing.mock import MockClient
from testing.mock import MockGuild
from testing.mock import MockUser
from threepseat.bot import Bot
from threepseat.ext.sounds.data import MAX_SOUND_FILE_SIZE_BYTES
from threepseat.ext.sounds.data import MemberSound
from threepseat.ext.sounds.data import MemberSoundTable
from threepseat.ext.sounds.data import Sound
from threepseat.ext.sounds.data import SoundsTable
from threepseat.ext.sounds.web import author_name
from threepseat.ext.sounds.web import create_app
from threepseat.ext.sounds.web import get_member
from threepseat.ext.sounds.web import get_mutual_guilds
from threepseat.ext.sounds.web import request_too_large


def _upload_file(
    content: bytes = b'fake mp3 data',
    filename: str = 'test.mp3',
) -> FileStorage:
    return FileStorage(stream=io.BytesIO(content), filename=filename)


@pytest.fixture
async def quart_app(
    tmp_file: str,
    tmp_path: pathlib.Path,
) -> AsyncGenerator[quart.typing.TestAppProtocol, None]:
    """Generate Quart test app."""
    data_path = str(tmp_path / 'sounds')
    sounds = SoundsTable(db_path=tmp_file, data_path=data_path)
    member_sounds = MemberSoundTable(db_path=tmp_file)

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
            member_sounds=member_sounds,
            client_id=1234,
            client_secret='1234',
            bot_token='1234',
            redirect_uri='http://localhost:5001',
            secret_key='test-secret-key',
        )

        async with app.test_app() as test_app:  # pragma: no branch
            yield test_app


async def test_index_authorized(quart_app) -> None:
    # Our test configuration sets authorized by default
    client = quart_app.test_client()

    response = await client.get('/')
    # Redirect to /guilds/
    assert response.status_code == HTTPStatus.FOUND
    location = [h for h in response.headers if 'location' in h].pop()
    assert location[1] == '/guilds/'


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
    assert response.status_code == HTTPStatus.OK


async def test_guilds(quart_app) -> None:
    client = quart_app.test_client()

    with mock.patch(
        'threepseat.ext.sounds.web.get_mutual_guilds',
        return_value=[MockGuild('guild1', 1), MockGuild('guild2', 2)],
    ):
        response = await client.get('/guilds/')

    assert response.status_code == HTTPStatus.OK


async def test_sound_grid(quart_app) -> None:
    client = quart_app.test_client()

    bot = quart_app.app.config['bot']
    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']

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

    # The user is authenticated but has no registered entrance sound.
    user = mock.MagicMock()
    user.id = 999

    with (
        mock.patch.object(sounds, 'all', return_value=sound_list),
        mock.patch.object(bot, 'get_guild', return_value=guild),
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=user),
        ),
    ):
        response = await client.get('/sounds/1234')

    assert response.status_code == HTTPStatus.OK
    assert b'entrance-btn active' not in await response.get_data()


async def test_sound_grid_marks_entrance_sound(quart_app) -> None:
    client = quart_app.test_client()

    bot = quart_app.app.config['bot']
    sounds = quart_app.app.config['sounds']
    member_sounds = quart_app.app.config['member_sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']

    guild = MockGuild('name', 1)
    sound = Sound(
        uuid='1',
        name='sound1',
        description='a sound',
        link='',
        author_id=1234,
        guild_id=1234,
        created_time=0,
        filename='',
    )

    # The current user has registered 'sound1' as their entrance sound.
    member_sounds.update(
        MemberSound(
            member_id=555,
            guild_id=1234,
            name='sound1',
            updated_time=0,
        ),
    )
    user = mock.MagicMock()
    user.id = 555

    with (
        mock.patch.object(sounds, 'all', return_value=[sound]),
        mock.patch.object(bot, 'get_guild', return_value=guild),
        mock.patch.object(
            discord,
            'fetch_user',
            mock.AsyncMock(return_value=user),
        ),
    ):
        response = await client.get('/sounds/1234')

    assert response.status_code == HTTPStatus.OK
    # The matching card's star badge is rendered active.
    assert b'entrance-btn active' in await response.get_data()


def test_author_name() -> None:
    # Resolved directly as a guild member.
    guild = mock.MagicMock()
    member = mock.MagicMock()
    member.display_name = 'Greg'
    guild.get_member.return_value = member
    assert author_name(mock.MagicMock(), guild, 1) == 'Greg'

    # No guild member; fall back to a global user lookup.
    client = mock.MagicMock()
    user = mock.MagicMock()
    user.display_name = 'Bob'
    client.get_user.return_value = user
    assert author_name(client, None, 1) == 'Bob'

    # Unknown when neither the guild nor the client resolves the id.
    client_none = mock.MagicMock()
    client_none.get_user.return_value = None
    assert author_name(client_none, None, 1) == 'unknown'


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
        response = await client.post('/sounds/1234/mysound/play')
        assert mocked.await_count == 1

    assert response.status_code == HTTPStatus.OK


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
        response = await client.post('/sounds/1234/mysound/play')
        assert mocked.await_count == 0

    assert response.status_code == HTTPStatus.BAD_REQUEST


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
        response = await client.post('/sounds/1234/mysound/play')
        assert mocked.await_count == 0

    assert response.status_code == HTTPStatus.BAD_REQUEST


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
        response = await client.post('/sounds/1234/mysound/play')
        assert mocked.await_count == 0

    assert response.status_code == HTTPStatus.BAD_REQUEST


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
        response = await client.post('/sounds/1234/mysound/play')
        assert mocked.await_count == 1

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_set_entrance_new(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    member_sounds = quart_app.app.config['member_sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(sounds, 'get', return_value=object()),
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
        response = await client.post('/sounds/5678/mysound/entrance')

    assert response.status_code == HTTPStatus.OK
    body = await response.get_json()
    assert body == {'active': True, 'name': 'mysound'}
    saved = member_sounds.get(member_id=1234, guild_id=5678)
    assert saved is not None
    assert saved.name == 'mysound'


async def test_set_entrance_toggle_clear(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    member_sounds = quart_app.app.config['member_sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    # Pre-register the same sound so the toggle clears it.
    member_sounds.update(
        MemberSound(
            member_id=1234,
            guild_id=5678,
            name='mysound',
            updated_time=0,
        ),
    )

    with (
        mock.patch.object(sounds, 'get', return_value=object()),
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
        response = await client.post('/sounds/5678/mysound/entrance')

    assert response.status_code == HTTPStatus.OK
    body = await response.get_json()
    assert body == {'active': False, 'name': 'mysound'}
    assert member_sounds.get(member_id=1234, guild_id=5678) is None


async def test_set_entrance_no_member(quart_app) -> None:
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
        response = await client.post('/sounds/5678/mysound/entrance')

    assert response.status_code == HTTPStatus.BAD_REQUEST


async def test_set_entrance_no_sound(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    with (
        mock.patch.object(sounds, 'get', return_value=None),
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
        response = await client.post('/sounds/5678/mysound/entrance')

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'Unable to locate' in await response.get_data()


async def test_sound_file_success(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']

    # Persist a real sound so the file exists on disk to be served.
    sound = Sound.new(
        name='mysound',
        description='a test sound',
        link=None,
        author_id=1234,
        guild_id=5678,
    )
    pathlib.Path(sounds.filepath(sound.filename)).write_bytes(b'id3 audio')
    sounds.add(sound)

    response = await client.get('/sounds/5678/mysound/file')

    assert response.status_code == HTTPStatus.OK
    assert response.content_type == 'audio/mpeg'
    assert await response.get_data() == b'id3 audio'


async def test_sound_file_missing(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']

    with mock.patch.object(sounds, 'get', return_value=None):
        response = await client.get('/sounds/5678/nope/file')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert b'Unable to locate' in await response.get_data()


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
    mutual_guilds = [MockGuild('guild', 1)]

    with (
        mock.patch.object(client, 'get_user', return_value=mock_user),
        mock.patch(
            'discord.User.mutual_guilds',
            new_callable=mock.PropertyMock(return_value=mutual_guilds),
        ),
    ):
        assert get_mutual_guilds(client, user) == mutual_guilds


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
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            mock.AsyncMock(return_value=1.0),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == HTTPStatus.OK
    # The sound was actually persisted to the table.
    assert sounds.get('mysound', guild_id=5678) is not None


async def test_sound_add_video_success(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    # extract_audio would write the MP3; emulate it so table.add finds the
    # file on disk.
    async def fake_extract(_source, mp3_path) -> None:
        pathlib.Path(mp3_path).touch()

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
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            mock.AsyncMock(return_value=1.0),
        ),
        mock.patch(
            'threepseat.ext.sounds.data.extract_audio',
            side_effect=fake_extract,
        ) as mock_extract,
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'fromvideo', 'description': 'a video sound'},
            files={'file': _upload_file(filename='clip.mp4')},
        )

    assert response.status_code == HTTPStatus.OK
    assert mock_extract.call_count == 1
    assert sounds.get('fromvideo', guild_id=5678) is not None


async def test_sound_add_unsupported_type(quart_app) -> None:
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
            form={'name': 'badtype', 'description': 'a test sound'},
            files={'file': _upload_file(filename='clip.mkv')},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'supported video' in await response.get_data()


@pytest.mark.parametrize(
    'name',
    ['../../evil', 'has space', '', 'a' * 100],
)
async def test_sound_add_invalid_name(quart_app, name: str) -> None:
    # The name is interpolated into the sound's filename, so an invalid one
    # must be rejected before anything is written to disk.
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    # Look above the sounds directory too: a '../' name would land there.
    search_root = pathlib.Path(sounds.data_path).parent
    before = set(search_root.rglob('*.mp3'))

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
            form={'name': name, 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'Name must' in await response.get_data()
    assert set(search_root.rglob('*.mp3')) == before


async def test_sound_add_video_extract_error(quart_app) -> None:
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
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            mock.AsyncMock(return_value=1.0),
        ),
        mock.patch(
            'threepseat.ext.sounds.data.extract_audio',
            mock.AsyncMock(
                side_effect=ValueError(
                    'Could not extract audio from the video.',
                ),
            ),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'badvideo', 'description': 'a test sound'},
            files={'file': _upload_file(filename='clip.mov')},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'Could not extract audio' in await response.get_data()
    assert sounds.get('badvideo', guild_id=5678) is None


async def test_sound_add_video_too_long(quart_app) -> None:
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
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            mock.AsyncMock(return_value=999.0),
        ),
        mock.patch(
            'threepseat.ext.sounds.data.extract_audio',
            mock.AsyncMock(),
        ) as mock_extract,
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'longvideo', 'description': 'a test sound'},
            files={'file': _upload_file(filename='clip.mp4')},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'too long' in await response.get_data()
    # Rejected before any extraction and nothing was persisted.
    assert mock_extract.await_count == 0
    assert sounds.get('longvideo', guild_id=5678) is None


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

    assert response.status_code == HTTPStatus.BAD_REQUEST


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

    assert response.status_code == HTTPStatus.BAD_REQUEST


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

    assert response.status_code == HTTPStatus.BAD_REQUEST


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

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'MP3' in await response.get_data()


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

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'Description' in await response.get_data()


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

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'File size' in await response.get_data()


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
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            mock.AsyncMock(return_value=999.0),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'too long' in await response.get_data()
    # The partially-written file was cleaned up and nothing was persisted.
    assert sounds.get('mysound', guild_id=5678) is None


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
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            mock.AsyncMock(return_value=1.0),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'already exists' in await response.get_data()


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
            'threepseat.ext.sounds.data.mp3_duration_seconds',
            mock.AsyncMock(side_effect=RuntimeError('probe failed')),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={'name': 'mysound', 'description': 'a test sound'},
            files={'file': _upload_file()},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'Failed to save' in await response.get_data()


async def test_sound_add_youtube_success(quart_app) -> None:
    client = quart_app.test_client()

    sounds = quart_app.app.config['sounds']
    discord = quart_app.app.config['DISCORD_OAUTH2_SESSION']
    member = mock.MagicMock()
    member.id = 1234

    # download() would fetch and write the mp3; emulate it creating the file
    # so that SoundsTable.add finds it on disk.
    def fake_download(_link: str, filepath: str) -> None:
        pathlib.Path(filepath).touch()

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
            'threepseat.ext.sounds.web.download',
            side_effect=fake_download,
        ) as mock_download,
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={
                'name': 'mysound',
                'description': 'a test sound',
                'link': 'https://youtube.com/watch?v=abc',
            },
        )

    assert response.status_code == HTTPStatus.OK
    assert mock_download.call_count == 1
    saved = sounds.get('mysound', guild_id=5678)
    assert saved is not None
    assert saved.link == 'https://youtube.com/watch?v=abc'


async def test_sound_add_youtube_error(quart_app) -> None:
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
            'threepseat.ext.sounds.web.download',
            side_effect=ValueError('Clip is longer than 30 seconds.'),
        ),
    ):
        response = await client.post(
            '/sounds/5678/add',
            form={
                'name': 'mysound',
                'description': 'a test sound',
                'link': 'https://youtube.com/watch?v=abc',
            },
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'longer than' in await response.get_data()
    assert sounds.get('mysound', guild_id=5678) is None


async def test_sound_add_link_and_file(quart_app) -> None:
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
            form={
                'name': 'mysound',
                'description': 'a test sound',
                'link': 'https://youtube.com/watch?v=abc',
            },
            files={'file': _upload_file()},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert b'not both' in await response.get_data()


async def test_request_too_large_handler() -> None:
    # Uploads exceeding MAX_CONTENT_LENGTH are rejected by the ASGI server
    # with a 413 before reaching the handler; verify the friendly response.
    response = await request_too_large(Exception())
    assert isinstance(response, quart.Response)
    assert response.status_code == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    assert b'File size' in await response.get_data()


def test_secret_key_configured(quart_app) -> None:
    # A configured secret_key is used verbatim so sessions persist across
    # restarts.
    assert quart_app.app.secret_key == 'test-secret-key'


def _make_app(secret_key: str | None, tmp_file: str, data_path: str):
    sounds = SoundsTable(db_path=tmp_file, data_path=data_path)
    member_sounds = MemberSoundTable(db_path=tmp_file)
    with (
        mock.patch('threepseat.bot.Bot.user'),
        mock.patch('threepseat.bot.Bot.wait_until_ready'),
        mock.patch('discord.app_commands.tree.CommandTree.sync'),
        mock.patch('quart_discord._http.OAuth2Session'),
        mock.patch('quart_discord.client.DiscordOAuth2Session.fetch_user'),
    ):
        return create_app(
            bot=Bot(),
            sounds=sounds,
            member_sounds=member_sounds,
            client_id=1234,
            client_secret='1234',
            bot_token='1234',
            redirect_uri='http://localhost:5001',
            secret_key=secret_key,
        )


def test_secret_key_generated_warns(
    tmp_file: str,
    tmp_path: pathlib.Path,
    caplog,
) -> None:
    # Omitting secret_key still yields a usable key, but warns that sessions
    # won't persist across restarts.
    data_path = str(tmp_path / 'sounds')
    with caplog.at_level(logging.WARNING):
        app = _make_app(None, tmp_file, data_path)

    assert app.secret_key  # a key was generated
    assert 'secret_key' in caplog.text

    # The warning matters because each app generates its own key, so a
    # restart invalidates every existing session.
    other = _make_app(None, tmp_file, str(tmp_path / 'sounds2'))
    assert other.secret_key != app.secret_key
