import asyncio
import nest_asyncio
import os

from flask import Flask, redirect, url_for, jsonify, abort
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized

from threepseat.bot import Bot

nest_asyncio.apply()

app = Flask(__name__)
discord = DiscordOAuth2Session()


def get_app(
    bot_instance: Bot,
    port: int,
    discord_client_id: str,
    discord_client_secret: str,
    discord_bot_token: str
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
    bot = bot_instance
    app.secret_key = os.urandom(128)
    app.config['DISCORD_CLIENT_ID'] = discord_client_id
    app.config['DISCORD_CLIENT_SECRET'] = discord_client_secret
    app.config['DISCORD_BOT_TOKEN'] = discord_bot_token
    app.config['DISCORD_REDIRECT_URI'] = f'http://localhost:{port}/callback'

    discord.init_app(app)
    return app

def bot_exec(coro):
    return bot.loop.run_until_complete(coro)

@app.route('/login/')
def login():
    return discord.create_session()

@app.route('/callback/')
def callback():
    discord.callback()
    user = discord.fetch_user()
    return redirect(url_for('me'))

@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for('login'))

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
    user = bot.get_user(discord.fetch_user().id)
    mutual_guild_ids = [g.id for g in user.mutual_guilds]

    guilds = {}
    for guild in discord.fetch_guilds():
        if guild.id in mutual_guild_ids:
            guilds[guild.id] = {
                'id': guild.id,
                'name': guild.name,
                'icon_url': guild.icon_url,
            }

    return jsonify(guilds)

@app.route('/sounds/<guild_id>')
@requires_authorization
def sounds(guild_id):
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        abort(400)

    data = bot.get_cog('Voice').sounds(guild)
    return jsonify(data)

@app.route('/sounds/play/<guild_id>/<sound>')
@requires_authorization
def play(guild_id, sound):
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        abort(400)
    member = guild.get_member(discord.fetch_user().id)

    if member.voice is None or member.voice.channel is None:
        abort(400)
    
    try:
        #import threading
        #threading.Thread(
        #    target=bot.get_cog('Voice').play, args=(member.voice.channel, sound)
        #).start()
        #asyncio.run(bot.get_cog('Voice').play(member.voice.channel, sound))
        #bot.loop.run_until_complete(bot.get_cog('Voice').play(member.voice.channel, sound))
        bot_exec(bot.get_cog('Voice').play(member.voice.channel, sound))
    #finally:
    #    return 'success'
    except Exception as e:
        return str(e)
    return 'success'
