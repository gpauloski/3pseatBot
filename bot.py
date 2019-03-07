import discord, os, datetime
from utils import Bans, getTime
from discord.ext import	commands
from tinydb import TinyDB, Query
from dotenv import load_dotenv

# TODO
# - Meme of the day command

# Load token from .env
load_dotenv(verbose=True)
TOKEN = os.getenv("TOKEN")
NETWORKNAME = os.getenv("NETWORKNAME")
NETWORKPASS = os.getenv("NETWORKPASS")
SERVERIP = os.getenv("SERVERIP")

# Initialize bot
bot = commands.Bot(command_prefix='!')

# Max global offenses
MAX_OFFENSE = 3

# Create database
db = Bans()

@bot.command(name='3pseat', pass_context=True, brief='What are 3pseat\'s rules?')
async def _3pseat(ctx):
    msg = '3pseat {0.author.mention}, you must start all messages with 3pseat'.format(ctx.message)
    await bot.send_message(ctx.message.channel, msg)

@bot.command(name='list', pass_context=True, brief='List the strikes')
async def _list(ctx):
    msg = '3pseat {0.author.mention}, here are the strikes:'.format(ctx.message)
    serverCount = 0
    for user in db.getDB(ctx.message.server.name):
    	if user['name'] != 'server':
    	    msg = msg + '\n{0}: {1}/{2}'.format(user['name'], user['count'], MAX_OFFENSE)
    	else:
    		serverCount = user['count']
    msg = msg + '\nTotal offenses to date: {0}'.format(serverCount)
    await bot.send_message(ctx.message.channel, msg)

@bot.command(name='source', pass_context=True, brief='3pseatBot source code')
async def _3pseat(ctx):
    msg = '3pseatBot\'s source code can be found here: https://github.com/gpauloski/3pseatBot'.format(ctx.message)
    await bot.send_message(ctx.message.channel, msg)

# @bot.command(name='mc', pass_context=True, brief='Minecraft Server Login')
# async def _3pseat(ctx):
#     if ctx.message.server.name == "Little Plops":
#         msg = '3pseat: To login to the StoneBlock2 server:\n'.format(ctx.message)
#         msg = msg + '  1. Download the StoneBlock2 FTB pack in the Twitch launcher\n'
#         msg = msg + '  2. Download and install logmein Hamachi\n'
#         msg = msg + '  3. In Hamachi, go to Network->Join an existing network\n'
#         msg = msg + '       Network ID : {0}\n'.format(NETWORKNAME)
#         msg = msg + '       Network Password : {0}\n'.format(NETWORKPASS)
#         msg = msg + '  4. Join the server using IP : {0}\n'.format(SERVERIP)
#         msg = msg + 'Message @Atomos#2059 for whitelist'
#         await bot.send_message(ctx.message.channel, msg)

@bot.event
async def on_message(message):
    if message.author == bot.user or message.content.startswith('!'):
        await bot.process_commands(message)
    elif not message.content.lower().startswith('3pseat') and message.embeds is None:
        count = db.up(message.server.name, message.author.name)
        if count >= MAX_OFFENSE:
            db.clear(message.server.name, message.author.name)
            msg = '3pseat I\'m sorry {0.author.mention}, your time as come. RIP.'.format(message)
            await bot.send_message(message.channel, msg)
            await bot.kick(message.author)
            msg = '3pseat Press F to pay respects'.format(message)
            await bot.send_message(message.channel, msg)
            print(getTime() + ' ' + message.server.name + ': ' + message.author.name + ' made a fatal mistake')
        else:
            msg = '3pseat {0.author.mention}! You\'ve disturbed the spirits'.format(message)
            msg = msg + ' ('+ str(count) + '/' + str(MAX_OFFENSE) + ')'
            await bot.send_message(message.channel, msg)
            print(getTime() + ' ' + message.server.name + ': ' + message.author.name + ' made a mistake (' + str(count) + '/' + str(MAX_OFFENSE) + ')')

@bot.event
async def on_message_delete(message):
    if message.author == bot.user:
        return
    msg = '3pseat {0.author.mention} where\'d your message go? It was:\n{0.clean_content}'.format(message)
    await bot.send_message(message.channel, msg)
    print(getTime() + ' ' + message.server.name + ': ' + message.author.name + ' deleted something')

@bot.event
async def on_message_edit(before, after):
    if after.author == bot.user:
        return
    if after.embeds is not None:
        return
    msg = '3pseat {0.author.mention} why\'d you change your message? In case you forgot, it was:\n{0.clean_content}'.format(before)
    await bot.send_message(before.channel, msg)
    print(getTime() + ' ' + before.server.name + ': ' + before.author.name + ' edited their message')

@bot.event
async def on_ready():
    await bot.change_presence(game=discord.Game(name="3pseat Simulator 2019", type=1))
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.run(TOKEN)
