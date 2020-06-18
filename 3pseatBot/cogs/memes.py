import re
import random

from discord.ext import commands

#POG_RE = r'(^| |\'|")p+\s*o+\s*g+\s*g*\s*e*\s*r*\s*s*(c\s*h\s*a\s*m\s*p\s*)?(.| |$|\'|")'
POG_RE = r'(p+\s*)+(o+\s*)+(g+\s*)+'
#POG_EMOTE_RE = r'<:pog(gers*)?:\d*>'
POG_EMOTE_RE = r'<:.*pog.*:\d*>'
POG_EMOTES = ['\U0001F1F5', '\U0001F1F4', '\U0001F1EC']
DAD_RE = r'(^| |\n)((i\'?m)|(i am)) (\w+)'

class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def troll_reply(self, message):
        text = message.content.lower()
        if re.search(POG_RE, text) or re.search(POG_EMOTE_RE, text):
            await self.bot.send_server_message(message.channel, 'poggers', 
                    POG_EMOTES)

        search = re.findall(DAD_RE, text)
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

    @commands.command(name='flip', pass_context=True,
            brief='Flip a coin')
    async def _flip(self, ctx):
        rand = random.randint(1, 2)
        msg = 'heads' if rand == 1 else 'tails'
        await self.bot.send_server_message(ctx.channel, '{}'.format(msg))

def setup(bot):
    bot.add_cog(Memes(bot))
