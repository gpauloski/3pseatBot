from __future__ import annotations

import asyncio
import datetime
import logging
import os
import secrets
import time
from collections.abc import Awaitable
from collections.abc import Callable
from typing import NamedTuple
from typing import cast

import discord
import quart
from quart_discord import DiscordOAuth2Session
from quart_discord import Unauthorized
from quart_discord import models
from quart_discord import requires_authorization as _requires_authorization
from werkzeug.wrappers.response import Response as werkseug_Response

from threepseat.bot import Bot
from threepseat.ext.sounds.data import MAX_SOUND_DESCRIPTION_CHARS
from threepseat.ext.sounds.data import MAX_VIDEO_FILE_SIZE_BYTES
from threepseat.ext.sounds.data import MemberSound
from threepseat.ext.sounds.data import MemberSoundTable
from threepseat.ext.sounds.data import Sound
from threepseat.ext.sounds.data import SoundsTable
from threepseat.ext.sounds.data import download
from threepseat.ext.sounds.data import remove_if_exists
from threepseat.ext.sounds.data import save_upload
from threepseat.ext.sounds.data import validate_upload_extension
from threepseat.ext.sounds.data import validate_upload_size
from threepseat.utils import play_sound
from threepseat.utils import voice_channel

type Response = str | quart.Response | werkseug_Response


def requires_authorization[F: Callable[..., Awaitable[Response]]](
    view: F,
) -> F:
    """Typed wrapper for quart_discord's untyped `requires_authorization`.

    quart_discord ships no type stubs, so mypy treats the decorator (and
    anything it wraps) as `Any`. It preserves the wrapped view's signature
    via functools.wraps, so it's safe to re-assert that signature here.
    """
    return cast('F', _requires_authorization(view))


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


def create_app(  # noqa: PLR0913
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


class AppContext(NamedTuple):
    """Objects the routes need, resolved from the app config."""

    bot: Bot
    sounds: SoundsTable
    member_sounds: MemberSoundTable
    session: DiscordOAuth2Session


def context() -> AppContext:
    """Typed view of the objects create_app() stored on the app config.

    quart's config is a plain dict of Any, so reading it directly in each
    route discards the types. Resolving the keys in one place keeps the
    routes typed and the key names in a single spot.
    """
    config = quart.current_app.config
    return AppContext(
        bot=config['bot'],
        sounds=config['sounds'],
        member_sounds=config['member_sounds'],
        session=config['DISCORD_OAUTH2_SESSION'],
    )


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
        msg = f'Cannot find user {user.username}'
        raise ValueError(msg)
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
        logger.exception('failed to resolve author name for %s', author_id)
    return 'unknown'


async def resolve_member(
    guild_id: int,
) -> tuple[discord.Member | None, quart.Response | None]:
    """Resolve the current OAuth user to a member of the guild.

    Returns:
        a ``(member, None)`` pair on success, or ``(None, response)`` with a
        400 response to return to the caller when the user is not a member.
    """
    ctx = context()
    user = await ctx.session.fetch_user()
    member = get_member(ctx.bot, user, guild_id)
    if member is None:
        return None, quart.Response(
            'Cannot find your membership in the Guild.',
            400,
        )
    return member, None


@sounds_blueprint.route('/')
async def index() -> Response:
    """Home page."""
    if not await context().session.authorized:
        login_url = quart.url_for('sounds.login')
        return await quart.render_template('index.html', login_url=login_url)
    return quart.redirect(quart.url_for('sounds.guilds'))


@sounds_blueprint.route('/guilds/')
@requires_authorization
async def guilds() -> Response:
    """Select guild page."""
    ctx = context()
    user = await ctx.session.fetch_user()

    guilds = get_mutual_guilds(ctx.bot, user)

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
    ctx = context()
    sound_list = ctx.sounds.all(guild_id)
    guild = ctx.bot.get_guild(guild_id)

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
            author_name(ctx.bot, guild, sound.author_id),
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
        user = await ctx.session.fetch_user()
        current = ctx.member_sounds.get(member_id=user.id, guild_id=guild_id)
        if current is not None:
            entrance_sound = current.name
    except Exception:  # pragma: no cover
        logger.exception('failed to resolve entrance sound')

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
    sounds = context().sounds
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
        logger.exception('error playing sound')
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
    ctx = context()

    member, error = await resolve_member(guild_id)
    if error is not None:
        return error
    assert member is not None

    sound = ctx.sounds.get(sound_name, guild_id=guild_id)
    if sound is None:
        return quart.Response(
            f'Unable to locate a sound named {sound_name}.',
            400,
        )

    current = ctx.member_sounds.get(member_id=member.id, guild_id=guild_id)
    if current is not None and current.name == sound_name:
        ctx.member_sounds.remove(member_id=member.id, guild_id=guild_id)
        active = False
    else:
        ctx.member_sounds.update(
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
    sounds = context().sounds
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


class _SoundRequest(NamedTuple):
    """Validated contents of the add-a-sound form."""

    name: str
    description: str
    link: str
    content: bytes | None
    ext: str


async def _parse_sound_request() -> _SoundRequest:
    """Parse and validate the add-a-sound form.

    The upload is fully validated here so that sound_add() never writes an
    unchecked file to disk.

    Raises:
        ValueError:
            with a user-facing message if the form is invalid.
    """
    form = await quart.request.form
    files = await quart.request.files
    name = form.get('name', '').strip()
    description = form.get('description', '').strip()
    link = form.get('link', '').strip()
    file = files.get('file')
    has_file = file is not None and bool(file.filename)

    if len(description) == 0 or len(description) > MAX_SOUND_DESCRIPTION_CHARS:
        msg = (
            'Description must be between 1 and '
            f'{MAX_SOUND_DESCRIPTION_CHARS} characters.'
        )
        raise ValueError(msg)
    if link and has_file:
        msg = 'Provide either a YouTube link or an MP3 file, not both.'
        raise ValueError(msg)
    if not link and not has_file:
        msg = 'Provide a YouTube link or an MP3 or video file.'
        raise ValueError(msg)

    # A link is validated (including its duration) by download() later.
    content: bytes | None = None
    ext = ''
    if not link:
        assert file is not None
        ext = validate_upload_extension(file.filename or '')
        content = file.read()
        validate_upload_size(ext, len(content))

    return _SoundRequest(name, description, link, content, ext)


@sounds_blueprint.route('/sounds/<int:guild_id>/add', methods=['POST'])
@requires_authorization
async def sound_add(guild_id: int) -> Response:
    """Add a sound to a guild from a YouTube link or an uploaded MP3 file."""
    sounds = context().sounds

    member, error = await resolve_member(guild_id)
    if error is not None:
        return error
    assert member is not None

    try:
        request = await _parse_sound_request()
        # Sound.new validates the name, which is part of the filename, so
        # nothing below can write outside the sounds directory.
        sound = Sound.new(
            name=request.name,
            description=request.description,
            link=request.link or None,
            author_id=member.id,
            guild_id=guild_id,
        )
    except ValueError as e:
        return quart.Response(str(e), 400)

    filepath = sounds.filepath(sound.filename)

    logger.info(
        'processing sound upload %r from %s (%s) for guild %s (source: %s)',
        request.name,
        member.display_name,
        member.id,
        guild_id,
        'link' if request.link else request.ext.lstrip('.'),
    )

    try:
        if request.link:
            # download() enforces the duration limit and raises ValueError
            # on any download/extraction error. It is blocking, so run it in
            # a thread to avoid stalling the event loop.
            await asyncio.to_thread(download, request.link, filepath)
        else:
            assert request.content is not None
            await save_upload(request.content, request.ext, filepath)

        # add() validates the name (alphanumeric, length, uniqueness) and
        # that the file exists on disk.
        sounds.add(sound)
    except ValueError as e:
        remove_if_exists(filepath)
        return quart.Response(str(e), 400)
    except Exception:
        logger.exception('error saving uploaded sound')
        remove_if_exists(filepath)
        return quart.Response('Failed to save the sound.', 400)

    return quart.Response('', 200)


@sounds_blueprint.route('/login/')
async def login() -> Response:  # pragma: no cover
    """Login with discord OAuth."""
    session = context().session
    return cast('Response', await session.create_session(prompt=True))


@sounds_blueprint.route('/logout/')
async def logout() -> Response:  # pragma: no cover
    """Revoke discord OAuth."""
    context().session.revoke()
    return quart.redirect(quart.url_for('sounds.index'))


@sounds_blueprint.route('/callback/')
async def callback() -> Response:  # pragma: no cover
    """Discord OAuth callback route."""
    await context().session.callback()
    quart.session.permanent = True
    return quart.redirect(quart.url_for('sounds.guilds'))


@sounds_blueprint.errorhandler(Unauthorized)
async def redirect_unauthorized(_e: Exception) -> Response:  # pragma: no cover
    """Redirect to home if unauthorized."""
    return quart.redirect(quart.url_for('sounds.index'))


@sounds_blueprint.app_errorhandler(413)
async def request_too_large(_e: Exception) -> Response:
    """Return a friendly message when an upload exceeds the size limit."""
    mb = MAX_VIDEO_FILE_SIZE_BYTES // (1024 * 1024)
    logger.warning('rejected upload exceeding the %s MB limit', mb)
    return quart.Response(f'File size must be under {mb} MB.', 413)
