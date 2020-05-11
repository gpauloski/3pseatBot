import discord

from discord.ext import commands

class BotExtension(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='3pseat', pass_context=True, brief='What is 3pseat?')
    async def _threepseat(self, ctx):
        msg = '{}, you must start all messages with {}'.format(
              ctx.message.author.mention, self.bot.message_prefix[0])
        await self.bot.send_message(ctx.channel, msg)

    @commands.command(name='list', pass_context=True, brief='List the strikes')
    async def _list(self, ctx):
        msg = '3pseat {0.author.mention}, here are the strikes:'.format(
              ctx.message)
        serverCount = 0
        for user in self.bot.db.getDB(ctx.message.guild.name):
            if user['name'] != 'server':
    	        msg = msg + '\n{0}: {1}/{2}'.format(
                      user['name'], user['count'], MAX_OFFENSE)
            else:
                serverCount = user['count']
            msg = msg + '\nTotal offenses to date: {0}'.format(serverCount)
        await ctx.channel.send(msg)

    @commands.command(name='source', pass_context=True, 
                 brief='3pseatBot source code')
    async def _3pseat(self, ctx):
        msg = ('3pseatBot\'s source code can be found here: '
               'https://github.com/gpauloski/3pseatBot'.format(ctx.message))
        await ctx.channel.send(msg)

    @commands.command(name='mc', pass_context=True, brief='Minecraft Server Login')
    async def _mc(self, ctx):
        if (ctx.message.guild.name == "3pseat Little Plops" or
            ctx.message.guild.name == "BotTesting"):
            msg = '3pseat: To login to the vanilla server:\n'.format(ctx.message)
            msg = msg + 'Join the server using IP : {0}\n'.format(ZTIP)
            msg = msg + 'Message @Atomos#2059 for whitelist'
            await ctx.channel.send(msg)

    @commands.command(name='yeet', pass_context=True, brief='Yeet tha boi')
    async def _yeet(self, ctx, user: discord.User):
        await ctx.channel.send('3pseat yeeting {}'.format(user))
        #role = discord.utils.get(ctx.guild.roles, name='admin')
        #if not role in ctx.message.author.roles:
        if not ctx.message.author.guild_permissions.administrator:
            await ctx.channel.send('3pseat {0.author.mention}, you do not '
                                   'have yeet (admin) priviledge'.format(
                                   ctx.message))
        else:
            await ctx.guild.kick(user)

def setup(bot):
    bot.add_cog(BotExtension(bot))
