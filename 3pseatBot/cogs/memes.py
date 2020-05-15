import re
import random

from discord.ext import commands

class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def troll_reply(self, message):
        text = message.content.lower()
        if re.search(r'(^| )p+o+g+( |$)', text):
            await self.bot.send_server_message(message.channel, 'poggers')

        regex = r'(^| |\n)((i\'?m)|(i am)) (\w+)'
        search = re.findall(regex, text)
        if len(search) > 0:
            search = search[0]
            await self.bot.send_server_message(message.channel,
                    'Hi {}, I\'m {}!'.format(search[4], self.bot.user.mention))

    @commands.command(name='snowball', pass_context=True,
            brief='Should I snowball?')
    async def _snowball(self, ctx):
        msg = '{}, you should always take the snowball'.format(
              ctx.message.author.mention)
        await self.bot.send_server_message(ctx.channel, msg)

    @commands.command(name='odds', pass_context=True,
            brief='What are the odds? [max_num]')
    async def _odds(self, ctx, num: int):
        rand = random.randint(1, num)
        await self.bot.send_server_message(ctx.channel, '{}'.format(rand))

def setup(bot):
    bot.add_cog(Memes(bot))
