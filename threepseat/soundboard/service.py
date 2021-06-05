import logging
import nest_asyncio
import os
import random

from flask import Flask, redirect, url_for, jsonify, abort
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from threepseat.cogs import voice
from threepseat.bot import Bot
from threepseat.soundboard import error

nest_asyncio.apply()

app = Flask(__name__)
discord = DiscordOAuth2Session()
logger = logging.getLogger()
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=['10/second']
)

HYPERLINK = '<a href="{}">{}</a>'


def get_app(
    bot_instance: Bot,
    port: int,
    discord_client_id: str,
    discord_client_secret: str,
    discord_bot_token: str,
    static_site: bool = False
):
    """Create Flask app

    Args:
        bot (Bot)
        port (int): port flask is running on 
        discord_client_id (str): discord client id
        discord_client_secret (str): discord client secret
        discord_bot_token (str): discord bot token

    Returns
        Flask app
    """
    global bot
    global static
    bot = bot_instance
    static = static_site
    app.secret_key = os.urandom(128)
    app.config['DISCORD_CLIENT_ID'] = discord_client_id
    app.config['DISCORD_CLIENT_SECRET'] = discord_client_secret
    app.config['DISCORD_BOT_TOKEN'] = discord_bot_token
    app.config['DISCORD_REDIRECT_URI'] = f'http://localhost:{port}/callback'

    discord.init_app(app)
    return app


def bot_exec(coro):
    return bot.loop.run_until_complete(coro)


def get_mutual_guilds(user):
    user = bot.get_user(user.id)
    if user is None:
        raise error.UserNotFound(f'Cannot find user {user.username}')
    return {g.id: g for g in user.mutual_guilds}


def get_member_guild(user, guild_id):
    mutual_guilds = get_mutual_guilds(user)
    if len(mutual_guilds) == 0:
        raise error.UserHasNoMutualGuilds(
            f'{user.username} has no mutual guilds with {bot.username}'
        )
    if guild_id not in mutual_guilds:
        raise error.UserNotMemberOfGuild(
            f'{user.username} not a member of the requested guild'
        )
    guild = mutual_guilds[guild_id]
    member = guild.get_member(user.id)
    if member is None:
        raise error.MemberNotFound(
            f'Failed to get {user.username}\'s membership in {guild.name}'
        )
    return member, guild


@app.route('/login/')
def login():
    return discord.create_session()


@app.route('/callback/')
def callback():
    discord.callback()
    user = discord.fetch_user()
    return redirect(url_for('guilds'))


@app.route('/me/')
@requires_authorization
def me():
    user = discord.fetch_user()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'discriminator': user.discriminator,
        'bot': user.bot,
        'avatar_url': user.avatar_url,
        'default_avatar_url': user.default_avatar_url
    })


@app.route('/me/guilds/')
@requires_authorization
def guilds():
    guilds = {}
    mutual_guilds = get_mutual_guilds(discord.fetch_user())
    for guild in discord.fetch_guilds():
        if guild.id in mutual_guilds:
            guilds[guild.id] = {
                'id': guild.id,
                'name': guild.name,
                'icon_url': guild.icon_url,
            }

    if not static:
        return jsonify(guilds)

    s = 'Choose a guild: <br /><br />'
    for guild in guilds.values():
        url = HYPERLINK.format(
            url_for('sounds', guild_id=guild['id']), guild['name']
        )
        s += f'{url} <br \>'
    return s


@app.route('/sounds/<int:guild_id>')
@requires_authorization
def sounds(guild_id):
    member, guild = get_member_guild(discord.fetch_user(), guild_id)

    data = bot.get_cog('Voice').sounds(guild)

    if not static:
        return jsonify(data)

    sounds = sorted(data.keys())
    s = 'Click a sound to play: <br \><br \>'
    if len(sounds) == 0:
        s += 'No sounds found. <br \>'
    for sound in sounds:
        url = HYPERLINK.format(
            url_for('play', guild_id=guild_id, sound=sound), sound
        )
        s += f'{url} <br \>'

    url = HYPERLINK.format(url_for('roll', guild_id=guild_id), 'Roll a sound')
    s += f'<br \> {url}'
    return s


@app.route('/sounds/play/<int:guild_id>/<sound>')
@requires_authorization
@limiter.limit('1/second', override_defaults=True)
def play(guild_id, sound):
    member, guild = get_member_guild(discord.fetch_user(), guild_id)

    if member.voice is None or member.voice.channel is None:
        raise error.MemberNotInVoiceChannel(
            f'{member.name} is not in a voice channel'
        )
    
    try:
        bot_exec(bot.get_cog('Voice').play(member.voice.channel, sound))
    except voice.SoundNotFoundException as e:
        raise error.SoundNotFound(f'Sound {sound} not in {guild.name}')
    except Exception as e:
        logger.exception(e)
        raise error.FailedToPlaySound(
            f'Failed to play sound {sound} in {guild.name}'
        )

    if static:
        return redirect(url_for(f'sounds', guild_id=guild_id))
    return 'success'


@app.route('/sounds/roll/<int:guild_id>')
@requires_authorization
@limiter.limit('1/second', override_defaults=True)
def roll(guild_id):
    member, guild = get_member_guild(discord.fetch_user(), guild_id)

    if member.voice is None or member.voice.channel is None:
        raise error.MemberNotInVoiceChannel(
            f'{member.name} is not in a voice channel'
        )
    
    sounds = list(bot.get_cog('Voice').sounds(guild).keys())
    if len(sounds) == 0:
        raise error.NoSoundsInGuild(f'{guild.name} has no sounds')
    
    try:
        bot_exec(bot.get_cog('Voice').play(member.voice.channel, random.choice(sounds)))
    except Exception as e:
        raise error.FailedToPlaySound(
            f'Failed to play sound {sound} in {guild.name}'
        )
        logger.exception(e)

    if static:
        return redirect(url_for(f'sounds', guild_id=guild_id))
    return 'success'


@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for('login'))


@app.errorhandler(error.BaseError)
def handle_request_errors(e):
    response = jsonify({'type': e.__class__.__name__, 'message': e.message})
    response.status_code = e.error_code
    return response
