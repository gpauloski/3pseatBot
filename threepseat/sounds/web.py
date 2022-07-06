from __future__ import annotations

import logging
import os
from typing import TypeAlias

import quart
from quart_discord import DiscordOAuth2Session
from quart_discord import requires_authorization
from quart_discord import Unauthorized
from werkzeug.wrappers.response import Response as werkseug_Response

from threepseat.bot import Bot
from threepseat.sounds.data import Sounds

Response: TypeAlias = quart.Response | werkseug_Response

logger = logging.getLogger(__name__)

# Override Quart standard handlers
quart.logging.default_handler = logging.NullHandler()  # type: ignore
quart.logging.serving_handler = logging.NullHandler()  # type: ignore

sounds_blueprint = quart.Blueprint('sounds', __name__)


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

    if 'http://' in redirect_uri:
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


@sounds_blueprint.route('/')
@requires_authorization
async def index() -> Response:
    """Sounds home."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    user = await discord.fetch_user()

    return quart.jsonify(
        {
            'id': user.id,
            'username': user.username,
            'discriminator': user.discriminator,
            'bot': user.bot,
            'avatar_url': user.avatar_url,
            'default_avatar_url': user.default_avatar_url,
        },
    )


@sounds_blueprint.route('/login/')
async def login() -> Response:
    """Login with discord OAuth."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    return await discord.create_session()


@sounds_blueprint.route('/callback/')
async def callback() -> Response:
    """Discord OAuth callback route."""
    discord = quart.current_app.config['DISCORD_OAUTH2_SESSION']
    await discord.callback()
    return quart.redirect(quart.url_for('sounds.index'))


@sounds_blueprint.errorhandler(Unauthorized)
async def redirect_unauthorized(e: Exception) -> Response:
    """Redirect to login if unauthorized."""
    return quart.redirect(quart.url_for('sounds.login'))
