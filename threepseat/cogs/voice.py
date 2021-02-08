import discord
import json
import logging
import os
import youtube_dl

from discord.ext import commands, tasks
from typing import Dict


logger = logging.getLogger()

MAX_SOUND_LENGTH_SECONDS = 30


class Voice(commands.Cog):
    """

    Based on https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py
    """
    def __init__(self,
                 bot: commands.Bot,
                 sounds_dir: str) -> None:
        self.bot = bot
        self.sounds_dir = sounds_dir

        if not os.path.exists(self.sounds_dir):
            os.makedirs(self.sounds_dir)

        self.leave_on_empty.start()


    def is_connected(self, ctx: commands.Context) -> bool:
        return ctx.voice_client is None


    @commands.command(pass_context=True, brief='join voice channel')
    async def join(self, ctx: commands.Context) -> bool:
        """Ensure bot is connected to same voice channel as user. Returns True on success."""
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await self.bot.message_guild( 
                    '{}, you must be in a voice channel'.format(ctx.author.mention),
                    ctx.channel)
            return False

        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        return True


    @commands.command(pass_context=True, brief='set bot volume [0-100]')
    async def volume(self, ctx: commands.Context, volume: int) -> None:
        if ctx.voice_client is None:
            await self.bot.message_guild(
                    'not connected to a voice channel.',
                    ctx.channel)
        elif ctx.voice_client.source is not None:
            ctx.voice_client.source.volume = volume / 100
            await self.bot.message_guild(
                    'changed volume to {}%'.format(volume), ctx.channel)


    @commands.command(pass_context=True, brief='leave voice channel')
    async def leave(self, ctx: commands.Context) -> None:
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()


    @commands.command(pass_context=True, brief='play a sound: [name]')
    async def play(self, ctx: commands.Context, sound: str) -> None:
        if not await self.join(ctx):
            return
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        _sounds = self.get_sounds()
        try:
            source = _sounds[sound]
        except:
            await self.bot.message_guild( 
                    'unable to find sound {}'.format(sound), ctx.channel)
            return
        source = discord.FFmpegPCMAudio(source)
        voice_client = ctx.voice_client
        voice_client.play(source, after=None)
        voice_client.source = discord.PCMVolumeTransformer(voice_client.source, 1)


    @commands.group(pass_context=True, brief='?help sounds for more info')
    async def sounds(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.list(ctx)


    @sounds.command(pass_context=True, brief='list sounds')
    async def list(self, ctx: commands.Context) -> None:
        _sounds = self.get_sounds()
        _sounds = ' '.join(sorted(_sounds.keys()))
        await self.bot.message_guild( 
                'the available sounds are: {}'.format(_sounds), ctx.channel)


    @sounds.command(pass_context=True, brief='add a sound: [name] [url]')
    async def add(self, ctx: commands.Context, name: str, url: str) -> None:
        if name in self.get_sounds().keys():
            await self.bot.message_guild(
                    'a sound named `{}` already exists. '
                    'Please choose a different name.'.format(name),
                    ctx.channel)
            return

        path = os.path.join(self.sounds_dir, name)
        ydl_opts = {
            'outtmpl': path + '.%(ext)s',
            'format': 'worst',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'logger': logger,
            'socket_timeout': 30,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                metadata = ydl.extract_info(url, download=False, process=False)
                if int(metadata['duration']) > MAX_SOUND_LENGTH_SECONDS:
                    await self.bot.message_guild('video is too long. '
                            'Max length = {}s'.format(MAX_SOUND_LENGTH_SECONDS),
                            ctx.channel)
                    return
                ydl.download([url])
        except Exception as e:
            logger.exception('caught error downloading sound:\n{}'.format(e))

        if os.path.exists(path + '.mp3'):
            await self.bot.message_guild('added sound `{}`.'.format(name),
                    ctx.channel)
        else:
            await self.bot.message_guild('error downloading audio.'.format(name),
                    ctx.channel)


    def get_sounds(self) -> Dict[str, str]:
        sounds = {}
        for filename in os.listdir(self.sounds_dir):
            if filename.endswith('.mp3') or filename.endswith('.mp4'):
                sounds[os.path.splitext(filename)[0]] = os.path.join(
                        self.sounds_dir, filename)
        return sounds


    @tasks.loop(seconds=30.0)
    async def leave_on_empty(self) -> None:
        """Task that periodically checks if connected channels are empty and leaves"""
        for client in self.bot.voice_clients:
            if len(client.channel.members) <= 1:
                await client.disconnect()