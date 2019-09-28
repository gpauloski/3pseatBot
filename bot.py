import discord, os, datetime
from utils import Bans, getTime, troll
from discord.ext import	commands
from tinydb import TinyDB, Query
from dotenv import load_dotenv

# TODO
# - create 3pseatBans.json if it does not exist
# - Meme of the day command

# Load token from .env
load_dotenv(verbose=True)
TOKEN = os.getenv("TOKEN")
ZTIP = os.getenv("IP")

# Initialize bot
bot = commands.Bot(command_prefix='$')

# Max global offenses
MAX_OFFENSE = 3

# Create database
db = Bans()

@bot.command(name='3pseat', pass_context=True, brief='What are 3pseat\'s rules?')
async def _3pseat(ctx):
    msg = '3pseat {0.author.mention}, you must start all messages with 3pseat'.format(ctx.message)
    await ctx.channel.send(msg)

@bot.command(name='list', pass_context=True, brief='List the strikes')
async def _list(ctx):
    msg = '3pseat {0.author.mention}, here are the strikes:'.format(ctx.message)
    serverCount = 0
    for user in db.getDB(ctx.message.guild.name):
    	if user['name'] != 'server':
    	    msg = msg + '\n{0}: {1}/{2}'.format(user['name'], user['count'], MAX_OFFENSE)
    	else:
    		serverCount = user['count']
    msg = msg + '\nTotal offenses to date: {0}'.format(serverCount)
    await ctx.channel.send(msg)

@bot.command(name='source', pass_context=True, brief='3pseatBot source code')
async def _3pseat(ctx):
    msg = '3pseatBot\'s source code can be found here: https://github.com/gpauloski/3pseatBot'.format(ctx.message)
    await ctx.channel.send(msg)

@bot.command(name='mc', pass_context=True, brief='Minecraft Server Login')
async def _mc(ctx):
    if ctx.message.guild.name == "3pseat Little Plops" or ctx.message.guild.name == "BotTesting":
        msg = '3pseat: To login to the vanilla server:\n'.format(ctx.message)
        msg = msg + 'Join the server using IP : {0}\n'.format(ZTIP)
        msg = msg + 'Message @Atomos#2059 for whitelist'
        await ctx.channel.send(msg)

@bot.command(name='yeet', pass_context=True, brief='Yeet tha boi')
async def _yeet(ctx, user: discord.User):
	await ctx.channel.send('3pseat yeeting {}'.format(user))
	#role = discord.utils.get(ctx.guild.roles, name='admin')
	#if not role in ctx.message.author.roles:
	if not ctx.message.author.guild_permissions.administrator:
		await ctx.channel.send("3pseat {0.author.mention}, you do not have yeet (admin) priviledge".format(ctx.message))
	#elif role in user.roles:
#		await ctx.channel.send("3pseat {} has yeet priviledge, cannot be yeeted".format(user))
	else:
		await ctx.guild.kick(user)

@bot.event
async def on_message(message):
    if message.author == bot.user or message.content.startswith('!') or message.content.startswith('$') or message.content.startswith('<:') or message.author.bot:
        pass
    elif not message.content.lower().startswith('3pseat') and not message.attachments:
        count = db.up(message.guild.name, message.author.name)
        if count >= MAX_OFFENSE:
            db.clear(message.guild.name, message.author.name)
            msg = '3pseat I\'m sorry {0.author.mention}, your time as come. RIP.'.format(message)
            await message.channel.send(msg)
            if message.author.guild_permissions.administrator:
                msg = '3pseat Failed to kick {0.author.mention}, damn you.'.format(message)
                await message.channel.send(msg)
            else:
                await message.guild.kick(message.author)
                msg = '3pseat Press F to pay respects'.format(message)
                await message.channel.send(msg)
            print(getTime() + ' ' + message.guild.name + ': ' + message.author.name + ' made a fatal mistake')
        else:
            msg = '3pseat {0.author.mention}! You\'ve disturbed the spirits'.format(message)
            msg = msg + ' ('+ str(count) + '/' + str(MAX_OFFENSE) + ')'
            await message.channel.send(msg)
            print(getTime() + ' ' + message.guild.name + ': ' + message.author.name + ' made a mistake (' + str(count) + '/' + str(MAX_OFFENSE) + ')')
    elif message.content.lower().startswith('3pseat i\'m '):
        await message.channel.send(troll(message, 'i\'m'))
    elif message.content.lower().startswith('3pseat im '):
        await message.channel.send(troll(message, 'im'))
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author == bot.user:
        return
    msg = '3pseat {0.author.mention} where\'d your message go? It was:\n{0.clean_content}'.format(message)
    await message.channel.send(msg)
    print(getTime() + ' ' + message.guild.name + ': ' + message.author.name + ' deleted something')

@bot.event
async def on_message_edit(before, after):
    if before.author == bot.user:
        return
    if after.embeds:
        return
    msg = '3pseat {0.author.mention} why\'d you change your message? In case you forgot, it was:\n{0.clean_content}'.format(before)
    await message.channel.send(msg)
    print(getTime() + ' ' + before.guild.name + ': ' + before.author.name + ' edited their message')

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="3pseat Simulator 2019"))
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.run(TOKEN)
