import json
import os
import discord
import youtube_dl

from discord.ext import commands, tasks

MAX_SOUND_LENGTH_SECONDS = 30

class Voice(commands.Cog):
    """

    Based on https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py
    """
    def __init__(self, bot):
        self.bot = bot
        self.leave_on_empty.start()
        self.sounds_path = 'data/sounds'

    def is_connected(self, ctx):
        return ctx.voice_client is None

    @commands.command(name='join', pass_context=True, brief='Join voice channel')
    async def _join(self, ctx):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            return await self.bot.send_server_message(ctx.channel, 
                    '{}, you must be in a voice channel'.format(ctx.author.mention))
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command(name='volume', pass_context=True, brief='Set 3pseatBot volume: ?volume [0-100]')
    async def _volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await self.bot.send_server_message(ctx.channel,
                    'Not connected to a voice channel.')

        ctx.voice_client.source.volume = volume / 100
        await self.bot.send_server_message(ctx.channel,
                'Changed volume to {}%'.format(volume))

    @commands.command(name='leave', pass_context=True, brief='Leave voice channel')
    async def _leave(self, ctx):
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    @commands.command(name='play', pass_context=True, brief='Play a sound: ?play {name}')
    async def _play(self, ctx, sound: str):
        sounds = self.get_sounds()
        try:
            source = sounds[sound]
        except:
            await self.bot.send_server_message(ctx.channel, 
                    'unable to find sound {}'.format(sound))
            return
        source = discord.FFmpegPCMAudio(source)
        ctx.voice_client.play(source, after=None)

    @commands.command(name='addsound', pass_context=True, brief='Add a sound: ?addsound {name} {url}')
    async def _addsound(self, ctx, name: str, url: str):
        if name in self.get_sounds().keys():
            await self.bot.send_server_message(ctx.channel, 'a sound named `{}` already exists. '
                    'Please choose a different name.'.format(name))
            return

        path = os.path.join(self.sounds_path, name)
        ydl_opts = {
            'outtmpl': path + '.%(ext)s',
            'format': 'worst',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'logger': self.bot.logger,
            'socket_timeout': 30,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                metadata = ydl.extract_info(url, download=False, process=False)
                if int(metadata['duration']) > MAX_SOUND_LENGTH_SECONDS:
                    await self.bot.send_server_message(ctx.channel, 'video is too long. '
                            'Max length = {}s'.format(MAX_SOUND_LENGTH_SECONDS))
                    return
                ydl.download([url])
        except Exception as e:
            self.bot.log('Caught error downloading sound:\n{}'.format(e))

        if os.path.exists(path + '.mp3'):
            await self.bot.send_server_message(ctx.channel, 'added sound `{}`.'.format(name))
        else:
            await self.bot.send_server_message(ctx.channel, 'error downloading audio.'.format(name))


    @commands.command(name='sounds', pass_context=True, brief='List sounds')
    async def _sounds(self, ctx):
        sounds = self.get_sounds()
        sounds = ' '.join(sounds.keys())
        await self.bot.send_server_message(ctx.channel, 
                'the available sounds are: {}'.format(sounds))

    def get_sounds(self):
        sounds = {}
        for filename in os.listdir(self.sounds_path):
            if filename.endswith('.mp3') or filename.endswith('.mp4'):
                sounds[os.path.splitext(filename)[0]] = os.path.join(
                        self.sounds_path, filename)
        return sounds

    @_play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await self.bot.send_server_message(ctx.channel, 
                        'You are not connected to a voice channel.')
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @tasks.loop(seconds=30.0)
    async def leave_on_empty(self):
        if len(self.bot.voice_clients) > 0:
            if len(self.bot.voice_clients[0].channel.members) <= 1:
                await self.bot.voice_clients[0].disconnect()

def setup(bot):
    bot.add_cog(Voice(bot))

