from __future__ import annotations

import logging
import os
from typing import NamedTuple
from typing import TypeAlias

import discord
import quart
from quart_discord import DiscordOAuth2Session
from quart_discord import models
from quart_discord import requires_authorization
from quart_discord import Unauthorized
from werkzeug.wrappers.response import Response as werkseug_Response

from threepseat.bot import Bot
from threepseat.sounds.data import Sounds
from threepseat.utils import play_sound
from threepseat.utils import voice_channel

Response: TypeAlias = str | quart.Response | werkseug_Response

logger = logging.getLogger(__name__)

# Override Quart standard handlers
quart.logging.default_handler = logging.NullHandler()  # type: ignore
quart.logging.serving_handler = logging.NullHandler()  # type: ignore

sounds_blueprint = quart.Blueprint(
    'sounds',
    __name__,
    template_folder='sounds/templates',
    static_folder='sounds/static',
)


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


def create_app(
    *,
    bot: Bot,
    sounds: Sounds,
    client_id: int,
    client_secret: str,
    bot_token: str,
    redirect_uri: str,
) -> quart.Quart:
    """Create the Quart app for serving the web interface.

    Args:
        bot (Bot): bot instance to use for playing sounds.
        sounds (Sounds): sounds database.
        client_id (int): client ID of bot.
        client_secret (str): client secret of bot.
        bot_token (str): bot token.
        redirect_uri (str): discord OAuth redirect URI. Should match a URI in
            the bot's management page.

    Returns:
        Quart app.
    """
    app = quart.Quart(__name__)

    # Propagate custom handlers to Quart App and Serving loggers
    app_logger = quart.logging.create_logger(app)
    serving_logger = quart.logging.create_serving_logger()
    app_logger.handlers = logger.handlers
    serving_logger.handlers = logger.handlers

    app.secret_key = os.urandom(128)

    if 'http://' in redirect_uri:  # pragma: no branch
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

    app.config['DISCORD_CLIENT_ID'] = client_id
    app.config['DISCORD_CLIENT_SECRET'] = client_secret
    app.config['DISCORD_REDIRECT_URI'] = redirect_uri
    app.config['DISCORD_BOT_TOKEN'] = bot_token

    app.config['DISCORD_OAUTH2_SESSION'] = DiscordOAuth2Session(app)

    app.config['bot'] = bot
    app.config['sounds'] = sounds

    app.register_blueprint(sounds_blueprint, url_prefix='')

    return app


def get_mutual_guilds(
    client: discord.Client,
    user: models.User,
) -> list[discord.Guild]:
    """Get mutual guilds between user and client.

    Args:
        client (discord.Client)
        user (model.User)

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


@sounds_blueprint.route('/')
@requires_authorization
async def index() -> Response:
    """Sounds home."""
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

    return await quart.render_template('guilds.html', guilds=guild_data)


@sounds_blueprint.route('/sounds/<int:guild_id>')
@requires_authorization
async def sound_grid(guild_id: int) -> Response:
    """Display grid of available sounds in guild."""
    bot = quart.current_app.config['bot']
    sounds = quart.current_app.config['sounds']
    sound_list = sounds.list(guild_id)
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
        )
        for sound in sound_list
    ]

    return await quart.render_template(
        'sounds.html',
        guild=guild,
        sounds=sound_data,
    )


@sounds_blueprint.route('/play/<int:guild_id>/<sound_name>')
@requires_authorization
async def sound_play(guild_id: int, sound_name: str) -> Response:
    """Play a sound and redirect back to grid."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    bot = quart.current_app.config['bot']
    sounds = quart.current_app.config['sounds']
    user = await discord.fetch_user()
    member = get_member(bot, user, guild_id)

    redirect = quart.redirect(
        quart.url_for('sounds.sound_grid', guild_id=guild_id),
    )

    # TODO: handle error with popup
    if member is None:
        return redirect

    sound = sounds.get(sound_name, guild_id=guild_id)

    if sound is None:
        return redirect

    channel = voice_channel(member)
    if channel is None:
        return redirect

    try:
        await play_sound(sounds.filepath(sound.filename), channel)
    except Exception as e:  # pragma: no cover
        logger.exception(f'Error playing sound: {e}')

    return redirect


@sounds_blueprint.route('/login/')
async def login() -> Response:  # pragma: no cover
    """Login with discord OAuth."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    return await discord.create_session()


@sounds_blueprint.route('/callback/')
async def callback() -> Response:  # pragma: no cover
    """Discord OAuth callback route."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    await discord.callback()
    return quart.redirect(quart.url_for('sounds.index'))


@sounds_blueprint.errorhandler(Unauthorized)
async def redirect_unauthorized(e: Exception) -> Response:  # pragma: no cover
    """Redirect to login if unauthorized."""
    return quart.redirect(quart.url_for('sounds.login'))
