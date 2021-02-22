"""Cog for playing sound clips in voice channels"""
import discord
import logging
import os
import youtube_dl

from discord.ext import commands, tasks
from typing import Dict

from threepseat.bot import Bot


logger = logging.getLogger()

MAX_SOUND_LENGTH_SECONDS = 30


class Voice(commands.Cog):
    """Extension for playing sound clips in voice channels

    Based on https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py

    Adds the following commands:
      - `?join`: have bot join voice channel of user
      - `?leave`: have bot leave voice channel of user
      - `?volume [0-100]`: set volume
      - `?sounds`: aliases `?sounds list`
      - `?sounds play [name]`: play sound with name
      - `?sounds list`: list available sounds
      - `?sounds add [name] [youtube_url]`: download youtube audio and saves a sound with name
    """
    def __init__(self, bot: Bot, sounds_dir: str) -> None:
        """Init Voice

        Args:
            bot (Bot): bot that loaded this cog
            sounds_dir (str): directory to store audio files in
        """
        self.bot = bot
        self.sounds_dir = sounds_dir

        if not os.path.exists(self.sounds_dir):
            os.makedirs(self.sounds_dir)

        self._leave_on_empty.start()

    async def join(self, ctx: commands.Context) -> bool:
        """Join `ctx.author.voice.channel` if it exists

        Args:
            ctx (Context): context from command call

        Returns:
            `True` on successful join
        """
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

    async def leave(self, ctx: commands.Context) -> None:
        """Leave voice channel

        Args:
            ctx (Context): context from command call
        """
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

    async def volume(self, ctx: commands.Context, volume: int) -> None:
        """Set volume of audio source

        Warning:
            the volume is set on a per source basis so if nothing
            is playing, the volume cannot be set

        Args:
            ctx (Context): context from command call
            volume (int): volume value out of 100
        """
        if volume < 0:
            volume = 0
        elif volume > 100:
            volume = 100
        if ctx.voice_client is None:
            await self.bot.message_guild(
                'not connected to a voice channel.', ctx.channel)
        elif ctx.voice_client.source is not None:
            ctx.voice_client.source.volume = volume / 100
            await self.bot.message_guild(
                'changed volume to {}%'.format(volume), ctx.channel)

    async def play(self, ctx: commands.Context, sound: str) -> None:
        """Play the sound for `ctx.message.author`

        Args:
            ctx (Context): context from command call
            sound (str): name of sound to play
        """
        if not await self.join(ctx):
            return
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        _sounds = self.get_sounds()
        try:
            source = _sounds[sound]
        except KeyError:
            await self.bot.message_guild(
                'unable to find sound {}'.format(sound), ctx.channel)
            return
        source = discord.FFmpegPCMAudio(source)
        voice_client = ctx.voice_client
        voice_client.play(source, after=None)
        voice_client.source = discord.PCMVolumeTransformer(voice_client.source, 1)

    async def list(self, ctx: commands.Context) -> None:
        """List available sounds in `ctx.channel`

        Args:
            ctx (Context): context from command call
        """
        _sounds = self.get_sounds()
        _sounds = ' '.join(sorted(_sounds.keys()))
        await self.bot.message_guild(
            'the available sounds are: {}'.format(_sounds), ctx.channel)

    async def add(self, ctx: commands.Context, name: str, url: str) -> None:
        """Download audio from youtube video

        Args:
            ctx (Context): context from command call
            name (str): name for the sound
            url (str): youtube url to download
        """
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
                    msg = 'video is too long. Max length = {}s'.format(
                        MAX_SOUND_LENGTH_SECONDS)
                    await self.bot.message_guild(msg, ctx.channel)
                    return
                ydl.download([url])
        except Exception as e:
            logger.exception('caught error downloading sound:\n{}'.format(e))

        if os.path.exists(path + '.mp3'):
            await self.bot.message_guild(
                'added sound `{}`.'.format(name), ctx.channel)
        else:
            await self.bot.message_guild(
                'error downloading audio.', ctx.channel)

    def is_connected(self, ctx: commands.Context) -> bool:
        """Returns True is bot is connect to a voice channel"""
        return ctx.voice_client is None

    def get_sounds(self) -> Dict[str, str]:
        """Returns dict of sound names and filepaths"""
        sounds = {}
        for filename in os.listdir(self.sounds_dir):
            if filename.endswith('.mp3') or filename.endswith('.mp4'):
                sounds[os.path.splitext(filename)[0]] = os.path.join(
                    self.sounds_dir, filename)
        return sounds

    @tasks.loop(seconds=30.0)
    async def _leave_on_empty(self) -> None:
        """Task that periodically checks if connected channels are empty and leaves"""
        for client in self.bot.voice_clients:
            if len(client.channel.members) <= 1:
                await client.disconnect()

    @commands.command(name='join', pass_context=True, brief='join voice channel')
    async def _join(self, ctx: commands.Context) -> bool:
        await self.join(ctx)

    @commands.command(name='leave', pass_context=True, brief='leave voice channel')
    async def _leave(self, ctx: commands.Context) -> None:
        await self.leave(ctx)

    @commands.command(name='volume', pass_context=True, brief='set bot volume [0-100]')
    async def _volume(self, ctx: commands.Context, volume: int) -> None:
        await self.volume(ctx, volume)

    @commands.group(name='sounds', pass_context=True, brief='?help sounds for more info')
    async def _sounds(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.list(ctx)

    @_sounds.command(name='play', pass_context=True, brief='play a sound: [name]')
    async def _play(self, ctx: commands.Context, sound: str) -> None:
        await self.play(ctx, sound)

    @_sounds.command(name='list', pass_context=True, brief='list sounds')
    async def _list(self, ctx: commands.Context) -> None:
        await self.list(ctx)

    @_sounds.command(name='add', pass_context=True, brief='add a sound: [name] [url]')
    async def _add(self, ctx: commands.Context, name: str, url: str) -> None:
        await self.add(ctx, name, url)
