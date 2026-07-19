from __future__ import annotations

import asyncio
import datetime
import logging
import os
import secrets
import tempfile
import time
from typing import NamedTuple

import discord
import quart
from quart_discord import DiscordOAuth2Session
from quart_discord import Unauthorized
from quart_discord import models
from quart_discord import requires_authorization
from werkzeug.wrappers.response import Response as werkseug_Response

from threepseat.bot import Bot
from threepseat.ext.sounds.data import MAX_SOUND_DESCRIPTION_CHARS
from threepseat.ext.sounds.data import MAX_SOUND_FILE_SIZE_BYTES
from threepseat.ext.sounds.data import MAX_SOUND_LENGTH_SECONDS
from threepseat.ext.sounds.data import MAX_VIDEO_FILE_SIZE_BYTES
from threepseat.ext.sounds.data import SUPPORTED_VIDEO_EXTENSIONS
from threepseat.ext.sounds.data import MemberSound
from threepseat.ext.sounds.data import MemberSoundTable
from threepseat.ext.sounds.data import Sound
from threepseat.ext.sounds.data import SoundsTable
from threepseat.ext.sounds.data import download
from threepseat.ext.sounds.data import extract_audio
from threepseat.ext.sounds.data import mp3_duration_seconds
from threepseat.ext.sounds.data import supported_video_extensions_str
from threepseat.utils import play_sound
from threepseat.utils import voice_channel

type Response = str | quart.Response | werkseug_Response

logger = logging.getLogger(__name__)

sounds_blueprint = quart.Blueprint('sounds', __name__)


class GuildData(NamedTuple):
    """Guild data passed to guilds template."""

    name: str
    icon: str
    url: str


class SoundData(NamedTuple):
    """Sound data passed to sounds template."""

    name: str
    description: str
    youtube_link: str
    url: str
    author: str
    created: str
    created_ts: float


def create_app(
    *,
    bot: Bot,
    sounds: SoundsTable,
    member_sounds: MemberSoundTable,
    client_id: int,
    client_secret: str,
    bot_token: str,
    redirect_uri: str,
    secret_key: str | None = None,
) -> quart.Quart:
    """Create the Quart app for serving the web interface.

    Args:
        bot (Bot): bot instance to use for playing sounds.
        sounds (SoundsTable): sounds table.
        member_sounds (MemberSoundTable): table of members' voice-channel
            entrance sounds.
        client_id (int): client ID of bot.
        client_secret (str): client secret of bot.
        bot_token (str): bot token.
        redirect_uri (str): discord OAuth redirect URI. Should match a URI in
            the bot's management page.
        secret_key (str | None): key used to sign session cookies. When set,
            user logins persist across bot restarts. When None, an ephemeral
            key is generated and users must re-authenticate after each restart.

    Returns:
        Quart app.
    """
    app = quart.Quart(__name__)

    if secret_key:
        app.secret_key = secret_key
    else:
        app.secret_key = secrets.token_hex(64)
        logger.warning(
            'No secret_key is configured; generated an ephemeral key. Web '
            'sessions will not persist across restarts, so users must '
            're-authenticate with Discord each time the bot restarts. Set '
            '"secret_key" in the config to keep users logged in.',
        )

    # Cap request bodies so oversized uploads are rejected before we buffer
    # them. Size to the largest allowed upload (video) plus some headroom for
    # multipart overhead (form fields, boundaries); the exact file size is
    # validated in the upload handler for a friendlier error message.
    app.config['MAX_CONTENT_LENGTH'] = MAX_VIDEO_FILE_SIZE_BYTES + (
        1 * 1024 * 1024
    )

    if 'http://' in redirect_uri:  # pragma: no branch
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

    app.config['DISCORD_CLIENT_ID'] = client_id
    app.config['DISCORD_CLIENT_SECRET'] = client_secret
    app.config['DISCORD_REDIRECT_URI'] = redirect_uri
    app.config['DISCORD_BOT_TOKEN'] = bot_token

    app.config['DISCORD_OAUTH2_SESSION'] = DiscordOAuth2Session(app)

    app.config['bot'] = bot
    app.config['sounds'] = sounds
    app.config['member_sounds'] = member_sounds

    app.register_blueprint(sounds_blueprint, url_prefix='')

    return app


def get_mutual_guilds(
    client: discord.Client,
    user: models.User,
) -> list[discord.Guild]:
    """Get mutual guilds between user and client.

    Args:
        client (discord.Client): Discord client.
        user (model.User): Discord user.

    Returns:
        list of Guilds.
    """
    user_ = client.get_user(user.id)
    if user_ is None:
        raise ValueError(f'Cannot find user {user.username}')
    return user_.mutual_guilds


def get_member(
    client: discord.Client,
    user: models.User,
    guild_id: int,
) -> discord.Member | None:
    """Convert user to guild member."""
    guild = client.get_guild(guild_id)
    if guild is None:
        return None
    return guild.get_member(user.id)


def author_name(
    client: discord.Client,
    guild: discord.Guild | None,
    author_id: int,
) -> str:
    """Resolve a sound's author id to a display name.

    Falls back to 'unknown' if the uploader can no longer be resolved (e.g.
    they left the guild) so the grid always renders.
    """
    try:
        member = guild.get_member(author_id) if guild is not None else None
        if member is not None:
            return member.display_name
        resolved = client.get_user(author_id)
        if resolved is not None:
            return resolved.display_name
    except Exception:  # pragma: no cover
        pass
    return 'unknown'


async def resolve_member(
    guild_id: int,
) -> tuple[discord.Member | None, quart.Response | None]:
    """Resolve the current OAuth user to a member of the guild.

    Returns:
        a ``(member, None)`` pair on success, or ``(None, response)`` with a
        400 response to return to the caller when the user is not a member.
    """
    discord_session = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    bot = quart.current_app.config['bot']
    user = await discord_session.fetch_user()
    member = get_member(bot, user, guild_id)
    if member is None:
        return None, quart.Response(
            'Cannot find your membership in the Guild.',
            400,
        )
    return member, None


@sounds_blueprint.route('/')
async def index() -> Response:
    """Home page."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    if not await discord.authorized:
        login_url = quart.url_for('sounds.login')
        return await quart.render_template('index.html', login_url=login_url)
    else:
        return quart.redirect(quart.url_for('sounds.guilds'))


@sounds_blueprint.route('/guilds/')
@requires_authorization
async def guilds() -> Response:
    """Select guild page."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    bot = quart.current_app.config['bot']
    user = await discord.fetch_user()

    guilds = get_mutual_guilds(bot, user)

    guild_data = [
        GuildData(
            guild.name,
            guild.icon.url if guild.icon is not None else '',
            quart.url_for('sounds.sound_grid', guild_id=guild.id),
        )
        for guild in guilds
    ]

    guild_data.sort(key=lambda x: x.name)

    return await quart.render_template(
        'guilds.html',
        guilds=guild_data,
        logout_url=quart.url_for('sounds.logout'),
    )


@sounds_blueprint.route('/sounds/<int:guild_id>')
@requires_authorization
async def sound_grid(guild_id: int) -> Response:
    """Display grid of available sounds in guild."""
    bot = quart.current_app.config['bot']
    sounds = quart.current_app.config['sounds']
    sound_list = sounds.all(guild_id)
    guild = bot.get_guild(guild_id)

    sound_data = [
        SoundData(
            sound.name,
            sound.description,
            sound.link,
            quart.url_for(
                'sounds.sound_play',
                guild_id=guild_id,
                sound_name=sound.name,
            ),
            author_name(bot, guild, sound.author_id),
            datetime.datetime.fromtimestamp(
                sound.created_time,
                tz=datetime.UTC,
            ).strftime('%b %d, %Y'),
            sound.created_time,
        )
        for sound in sound_list
    ]

    sound_data.sort(key=lambda x: x.name.lower())

    guild_icon = (
        guild.icon.url if guild is not None and guild.icon is not None else ''
    )

    # The name of the current user's registered entrance sound (if any) so the
    # template can mark that card. Best-effort: never let it break the grid.
    entrance_sound: str | None = None
    try:
        discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
        member_sounds = quart.current_app.config['member_sounds']
        user = await discord.fetch_user()
        current = member_sounds.get(member_id=user.id, guild_id=guild_id)
        if current is not None:
            entrance_sound = current.name
    except Exception:  # pragma: no cover
        logger.exception('Failed to resolve entrance sound.')

    return await quart.render_template(
        'sounds.html',
        guild=guild,
        guild_id=guild_id,
        guild_icon=guild_icon,
        sounds=sound_data,
        entrance_sound=entrance_sound,
        logout_url=quart.url_for('sounds.logout'),
    )


@sounds_blueprint.route(
    '/sounds/<int:guild_id>/<sound_name>/play',
    methods=['POST'],
)
@requires_authorization
async def sound_play(guild_id: int, sound_name: str) -> Response:
    """Play a sound into the user's voice channel."""
    sounds = quart.current_app.config['sounds']
    member, error = await resolve_member(guild_id)
    if error is not None:
        return error
    assert member is not None

    sound = sounds.get(sound_name, guild_id=guild_id)
    if sound is None:
        return quart.Response(
            f'Unable to locate a sound named {sound_name}.',
            400,
        )

    channel = voice_channel(member)
    if channel is None:
        return quart.Response('You are not in a voice channel.', 400)

    sound_file = sounds.filepath(sound.filename)
    try:
        await play_sound(sound_file, channel)
    except Exception as e:
        logger.exception(f'Error playing sound: {e}.')
        return quart.Response(str(e), 400)
    else:
        return quart.Response('', 200)


@sounds_blueprint.route(
    '/sounds/<int:guild_id>/<sound_name>/entrance',
    methods=['POST'],
)
@requires_authorization
async def set_entrance(guild_id: int, sound_name: str) -> Response:
    """Toggle a sound as the user's voice-channel entrance sound.

    Setting the sound that is already registered clears it, so the same
    endpoint both selects and deselects.
    """
    sounds = quart.current_app.config['sounds']
    member_sounds = quart.current_app.config['member_sounds']

    member, error = await resolve_member(guild_id)
    if error is not None:
        return error
    assert member is not None

    sound = sounds.get(sound_name, guild_id=guild_id)
    if sound is None:
        return quart.Response(
            f'Unable to locate a sound named {sound_name}.',
            400,
        )

    current = member_sounds.get(member_id=member.id, guild_id=guild_id)
    if current is not None and current.name == sound_name:
        member_sounds.remove(member_id=member.id, guild_id=guild_id)
        active = False
    else:
        member_sounds.update(
            MemberSound(
                member_id=member.id,
                guild_id=guild_id,
                name=sound_name,
                updated_time=time.time(),
            ),
        )
        active = True

    return quart.jsonify({'active': active, 'name': sound_name})


@sounds_blueprint.route('/sounds/<int:guild_id>/<sound_name>/file')
@requires_authorization
async def sound_file(guild_id: int, sound_name: str) -> Response:
    """Serve a sound's MP3 for in-browser preview."""
    sounds = quart.current_app.config['sounds']
    sound = sounds.get(sound_name, guild_id=guild_id)
    if sound is None:
        return quart.Response(
            f'Unable to locate a sound named {sound_name}.',
            404,
        )
    return await quart.send_file(
        sounds.filepath(sound.filename),
        mimetype='audio/mpeg',
    )


@sounds_blueprint.route('/sounds/<int:guild_id>/add', methods=['POST'])
@requires_authorization
async def sound_add(guild_id: int) -> Response:
    """Add a sound to a guild from a YouTube link or an uploaded MP3 file."""
    sounds = quart.current_app.config['sounds']

    member, error = await resolve_member(guild_id)
    if error is not None:
        return error
    assert member is not None

    form = await quart.request.form
    files = await quart.request.files
    name = form.get('name', '').strip()
    description = form.get('description', '').strip()
    link = form.get('link', '').strip()
    file = files.get('file')
    has_file = file is not None and bool(file.filename)

    if len(description) == 0 or len(description) > MAX_SOUND_DESCRIPTION_CHARS:
        return quart.Response(
            'Description must be between 1 and '
            f'{MAX_SOUND_DESCRIPTION_CHARS} characters.',
            400,
        )
    if link and has_file:
        return quart.Response(
            'Provide either a YouTube link or an MP3 file, not both.',
            400,
        )

    # Validate the upload before touching disk. The YouTube link is
    # validated (including duration) by download() below.
    content: bytes | None = None
    ext = ''
    if not link and has_file:
        assert file is not None
        filename = file.filename or ''
        ext = os.path.splitext(filename.lower())[1]
        is_mp3 = ext == '.mp3'
        is_video = ext in SUPPORTED_VIDEO_EXTENSIONS
        if not is_mp3 and not is_video:
            return quart.Response(
                'The file must be an MP3 or a supported video '
                f'({supported_video_extensions_str()}).',
                400,
            )
        content = file.read()
        max_size = (
            MAX_SOUND_FILE_SIZE_BYTES if is_mp3 else MAX_VIDEO_FILE_SIZE_BYTES
        )
        if len(content) > max_size:
            mb = max_size // (1024 * 1024)
            return quart.Response(f'File size must be under {mb} MB.', 400)
    elif not link:
        return quart.Response(
            'Provide a YouTube link or an MP3 or video file.',
            400,
        )

    sound = Sound.new(
        name=name,
        description=description,
        link=link if link else None,
        author_id=member.id,
        guild_id=guild_id,
    )
    filepath = sounds.filepath(sound.filename)

    try:
        if link:
            # download() enforces the duration limit and raises ValueError
            # on any download/extraction error. It is blocking, so run it in
            # a thread to avoid stalling the event loop.
            await asyncio.to_thread(download, link, filepath)
        elif ext == '.mp3':
            assert content is not None
            with open(filepath, 'wb') as f:
                f.write(content)
            duration = await mp3_duration_seconds(filepath)
            if duration > MAX_SOUND_LENGTH_SECONDS:
                raise ValueError(
                    f'Sound is too long ({duration:.1f}s). Maximum length '
                    f'is {MAX_SOUND_LENGTH_SECONDS} seconds.',
                )
        else:
            # Video: probe the duration and strip the audio to an MP3.
            assert content is not None
            await _extract_video_audio(content, ext, filepath)

        # add() validates the name (alphanumeric, length, uniqueness) and
        # that the file exists on disk.
        sounds.add(sound)
    except ValueError as e:
        _remove_if_exists(filepath)
        return quart.Response(str(e), 400)
    except Exception as e:
        logger.exception(f'Error saving uploaded sound: {e}')
        _remove_if_exists(filepath)
        return quart.Response('Failed to save the sound.', 400)

    return quart.Response('', 200)


def _remove_if_exists(filepath: str) -> None:
    """Remove a file if it exists, ignoring missing files."""
    try:
        os.remove(filepath)
    except FileNotFoundError:  # pragma: no cover
        pass


async def _extract_video_audio(
    content: bytes,
    ext: str,
    filepath: str,
) -> None:
    """Probe an uploaded video's duration and strip its audio to filepath.

    Raises:
        ValueError:
            if the clip is longer than MAX_SOUND_LENGTH_SECONDS or the audio
            cannot be extracted.
    """
    with tempfile.NamedTemporaryFile(suffix=ext) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        duration = await mp3_duration_seconds(temp_file.name)
        if duration > MAX_SOUND_LENGTH_SECONDS:
            raise ValueError(
                f'Sound is too long ({duration:.1f}s). Maximum length '
                f'is {MAX_SOUND_LENGTH_SECONDS} seconds.',
            )
        await extract_audio(temp_file.name, filepath)


@sounds_blueprint.route('/login/')
async def login() -> Response:  # pragma: no cover
    """Login with discord OAuth."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    return await discord.create_session(prompt=True)


@sounds_blueprint.route('/logout/')
async def logout() -> Response:  # pragma: no cover
    """Revoke discord OAuth."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    discord.revoke()
    return quart.redirect(quart.url_for('sounds.index'))


@sounds_blueprint.route('/callback/')
async def callback() -> Response:  # pragma: no cover
    """Discord OAuth callback route."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    await discord.callback()
    quart.session.permanent = True
    return quart.redirect(quart.url_for('sounds.guilds'))


@sounds_blueprint.errorhandler(Unauthorized)
async def redirect_unauthorized(e: Exception) -> Response:  # pragma: no cover
    """Redirect to home if unauthorized."""
    return quart.redirect(quart.url_for('sounds.index'))


@sounds_blueprint.app_errorhandler(413)
async def request_too_large(e: Exception) -> Response:
    """Return a friendly message when an upload exceeds the size limit."""
    mb = MAX_VIDEO_FILE_SIZE_BYTES // (1024 * 1024)
    return quart.Response(f'File size must be under {mb} MB.', 413)
