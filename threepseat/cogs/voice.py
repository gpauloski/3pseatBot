"""Cog for playing sound clips in voice channels"""
import discord
import logging
import os
import random
import youtube_dl

from discord.ext import commands, tasks
from typing import Dict, Optional

from threepseat.bot import Bot
from threepseat.utils import GuildDatabase


logger = logging.getLogger()

MAX_SOUND_LENGTH_SECONDS = 30


class JoinVoiceChannelException(Exception):
    pass


class SoundNotFoundException(Exception):
    pass


class SoundExistsException(Exception):
    pass


class SoundExceedsLimitException(Exception):
    pass


class SoundDownloadException(Exception):
    pass


class Voice(commands.Cog):
    """Extension for playing sound clips in voice channels

    Based on https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py

    Adds the following commands:
      - `?join`: have bot join voice channel of user
      - `?leave`: have bot leave voice channel of user
      - `?sounds`: aliases `?sounds list`
      - `?sounds play [name]`: play sound with name
      - `?sounds roll`: play a random sound
      - `?sounds list`: list available sounds
      - `?sounds add [name] [youtube_url]`: download youtube audio and saves a sound with name
    """
    def __init__(self, bot: Bot, sounds_file: str, sounds_dir: str) -> None:
        """Init Voice

        Args:
            bot (Bot): bot that loaded this cog
            sounds_file (str): path to store sounds database
            sounds_dir (str): directory to store audio files in
        """
        self.bot = bot

        # Note: sounds stored as ./<sounds_dir>/<guild_id>/<sound_name>.mp3
        self.sounds_dir = sounds_dir
        self.db = GuildDatabase(sounds_file)

        self._leave_on_empty.start()

    async def join_channel(self, channel: discord.VoiceChannel) -> None:
        """Join voice channel

        Args:
            channel (VoiceChannel): voice channel to leave

        Raises:
            JoinVoiceChannelException
        """
        try:
            if channel.guild.voice_client is not None:
                await channel.guild.voice_client.move_to(channel)
                return
            await channel.connect()
        except Exception as e:
            logger.exception(
                f'Caught exception when trying to join voice channel '
                f'{channel}. Raising JoinVoiceChannelException instead.'
            )
            raise JoinVoiceChannelException

    async def leave_channel(self, guild: discord.Guild) -> None:
        """Leave voice channel for guild

        Args:
            guild (Guild): guild to leave voice channel in
        """
        if guild.voice_client is not None:
            await guild.voice_client.disconnect()

    async def play(self, channel: discord.VoiceChannel, sound: str) -> None:
        """Play the sound for `ctx.message.author`

        Args:
            channel (VoiceChannel): channel to play sound in
            sound (str): name of sound to play

        Raises:
            JoinVoiceChannelException:
                if unable to join channel
            SoundNotFoundException:
                if unable to find sound
        """
        await self.join_channel(channel)

        voice_client = channel.guild.voice_client
        if voice_client.is_playing():
            voice_client.stop()

        sound_data = self.db.value(channel.guild, sound)
        if sound_data is None:
            raise SoundNotFoundException(f'Unable to find sound {sound}')

        if 'path' not in sound_data or not os.path.isfile(sound_data['path']):
            # If entry is missing valid path, remove from database
            self.db.clear(channel.guild, sound)
            raise SoundNotFoundException(f'Unable to find sound {sound}')

        source = discord.FFmpegPCMAudio(sound_data['path'])
        voice_client.play(source, after=None)
        voice_client.source = discord.PCMVolumeTransformer(voice_client.source, 1)

    def sounds(self, guild: discord.Guild) -> dict:
        """Returns all sounds and metadata

        Args:
            guild (Guild)
        """
        return self.db.table(guild)

    def add(
        self,
        guild: discord.Guild,
        name: str,
        url: str,
        image_url: Optional[str] = None
    ) -> None:
        """Add a new sound from YouTube

        Args:
            guild (Guild): guild to add sound to 
            name (str): name for the sound
            url (str): youtube url to download
            image_url (str): optional url of image for soundboard

        Raises:
            SoundExistsException
                if sound with `name` already exists
            SoundExceedsLimitException
                if sound is too long
            SoundDownloadException
                if there is an error downloading the sound
        """
        sounds = self.sounds(guild)
        if name in sounds and os.path.isfile(sounds[name]['path']):
            raise SoundExistsException

        path = os.path.join(self.sounds_dir, str(guild.id))
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, f'{name}.mp3')

        ydl_opts = {
            'outtmpl': path,
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
                    raise SoundExceedsLimitException
                ydl.download([url])
        except Exception as e:
            logger.exception('Caught error downloading sound')
            raise SoundDownloadException

        self.db.set(guild, name, {
                'path': path,
                'url': url,
                'image_url': image_url
            }
        )

    @tasks.loop(seconds=30.0)
    async def _leave_on_empty(self) -> None:
        """Task that periodically checks if connected channels are empty and leaves"""
        for client in self.bot.voice_clients:
            if len(client.channel.members) <= 1:
                await client.disconnect()

    @commands.command(
        name='join',
        pass_context=True,
        brief='join voice channel',
        ignore_extra=False
    )
    async def _join(self, ctx: commands.Context) -> bool:
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await self.bot.message_guild(
                '{}, you must be in a voice channel'.format(ctx.author.mention),
                ctx.channel
            )
        else:
            await self.join_channel(ctx.author.voice.channel)

    @commands.command(
        name='leave',
        pass_context=True,
        brief='leave voice channel',
        ignore_extra=False
    )
    async def _leave(self, ctx: commands.Context) -> None:
        await self.leave_channel(ctx.guild)

    @commands.group(
        name='sounds',
        pass_context=True,
        brief='?help sounds for more info'
    )
    async def _sounds(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self._list(ctx)

    @_sounds.command(
        name='add',
        pass_context=True,
        brief='add a sound: [name] [url] [image_url]',
        ignore_extra=False
    )
    async def _add(
        self,
        ctx: commands.Context,
        name: str,
        url: str,
        image_url: Optional[str] = None
    ) -> None:
        try:
            self.add(ctx.guild, name, url, image_url)
        except SoundExistsException:
            await self.bot.message_guild(
                f'sound with name `{name}` already exists',
                ctx.channel
            )
        except SoundExceedsLimitException:
            await self.bot.message_guild(
                f'{ctx.author.mention}, the clip is too long '
                f'(max={MAX_SOUND_LENGTH_SECONDS}s)',
                ctx.channel
            )
        except SoundDownloadException:
            await self.bot.message_guild(
                f'error downloading video for `{name}`',
                ctx.channel
            )

    @_sounds.command(
        name='list',
        pass_context=True,
        brief='list sounds',
        ignore_extra=False
    )
    async def _list(self, ctx: commands.Context) -> None:
        sounds = self.sounds(ctx.guild)
        sounds = ' '.join(sorted(sounds.keys()))
        await self.bot.message_guild(
            f'the available sounds are: `{sounds}`',
            ctx.channel
        )

    @_sounds.command(
        name='play',
        pass_context=True,
        brief='play a sound: [name]',
        ignore_extra=False
    )
    async def _play(self, ctx: commands.Context, sound: str) -> None:
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await self.bot.message_guild(
                '{}, you must be in a voice channel'.format(ctx.author.mention),
                ctx.channel
            )
        try:
            await self.play(ctx.author.voice.channel, sound)
        except JoinVoiceChannelException:
            await self.bot.message_guild(
                'failed to join the voice channel',
                ctx.channel
            )
        except SoundNotFoundException:
            await self.bot.message_guild(
                f'unable to find sound `{sound}`',
                ctx.channel
            )
        except:
            logger.exception(
                f'Failed to play sound {sound} in guild {ctx.guild.id}'
            )

    @_sounds.command(
        name='roll',
        pass_context=True,
        brief='play a random sound',
        ignore_extra=False
    )
    async def _roll(self, ctx: commands.Context) -> None:
        sounds = list(self.sounds(ctx.guild).keys())
        if len(sounds) < 1:
            await self.bot.message_guild(
                f'there are no sounds available',
                ctx.channel
            )
        else:
            await self._play(ctx, random.choice(sounds))
