"""Cog for playing sound clips in voice channels"""
import discord
import logging
import os
import random
import youtube_dl

from discord.ext import commands, tasks
from typing import Optional

from threepseat.bot import Bot
from threepseat.utils import GuildDatabase, is_admin


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
      - `?sounds update [name] [key] [value]`: update data about a sound
      - `?sounds remove [name]`: remove a sound
    """

    def __init__(
        self,
        bot: Bot,
        sounds_file: str,
        sounds_dir: str,
    ) -> None:
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

        self.rebuild_database()
        self._leave_on_empty.start()

    def rebuild_database(self):
        """Scan and clean up database

        Checks for sounds that are missing and downloads if possible,
        deletes otherwise. Enforces schema.

        Each entry keyed by `sound` has the following attributes:
        `url`, `image_url`, `path`, `tag`.
        """
        logger.info('[VOICE] Scanning sounds database...')
        for guild_id, table in self.db.tables().items():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                logger.info(f'[VOICE] Failed to find guild {guild_id}')
                continue
            for sound in list(table.keys()):
                data = table[sound]
                # Check additional metadata exists
                if 'image_url' not in data:
                    data['image_url'] = None
                if 'url' not in data:
                    data['url'] = None
                if 'tag' not in data:
                    data['tag'] = None

                # If file does not exist, try to download, otherwise delete
                if not os.path.isfile(data['path']):
                    if 'url' in data and data['url'] is not None:
                        self.add(
                            guild,
                            sound,
                            data['url'],
                            image_url=data['image_url'],
                            tag=data['tag'],
                        )
                        logger.info(
                            f'[VOICE] Restored missing {sound} in {guild.name}'
                        )
                    else:
                        self.db.clear(guild, sound)
                        logger.info(
                            f'[VOICE] Removed invalid {sound} from {guild.name}'
                        )
                self.db.set(guild, sound, data)
        logger.info('[VOICE] Finished scanning sounds database')

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
        except Exception:
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
        voice_client.source = discord.PCMVolumeTransformer(
            voice_client.source, 1
        )

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
        *,
        image_url: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> None:
        """Add a new sound from YouTube

        Args:
            guild (Guild): guild to add sound to
            name (str): name for the sound
            url (str): youtube url to download
            image_url (str): optional url of image for soundboard
            tag (str): optional tag for sound

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
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }
            ],
            'logger': logger,
            'socket_timeout': 30,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                metadata = ydl.extract_info(url, download=False, process=False)
                if int(metadata['duration']) > MAX_SOUND_LENGTH_SECONDS:
                    raise SoundExceedsLimitException
                ydl.download([url])
        except Exception:
            logger.exception('Caught error downloading sound')
            raise SoundDownloadException

        self.db.set(
            guild,
            name,
            {'path': path, 'url': url, 'image_url': image_url, 'tag': tag},
        )

    def update(
        self,
        guild: discord.Guild,
        name: str,
        *,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> None:
        """Update and existing sound

        Args:
            guild (Guild): guild sound is in
            name (str): name of the sound
            url (str): update with new youtube url
            image_url (str): update with new image url
            tag (str): update with new tag

        Raises:
            SoundNotFoundException:
                if the sound cannot be found
        """
        sound_data = self.db.value(guild, name)
        if sound_data is None:
            raise SoundNotFoundException(f'Unable to find sound {name}')

        if image_url is not None:
            sound_data['image_url'] = image_url
        if tag is not None:
            sound_data['tag'] = tag
        # URL has changed so download new file
        if url != sound_data['url']:
            self.db.clear(guild, name)
            try:
                self.add(
                    guild,
                    name,
                    sound_data['url'],
                    image_url=sound_data['image_url'],
                    tag=sound_data['tag'],
                )
            except Exception as e:
                # Restore original state if there is an error
                self.db.set(guild, name, sound_data)
                raise e

    def remove(
        self, guild: discord.Guild, member: discord.Member, name: str
    ) -> None:
        """Remove a sound

        Requires bot admin permissions.

        Args:
            guild (Guild): guild sound is in
            member (Member): member issuing command
            name (str): name of the sound

        Raises:
            SoundNotFoundException:
                if the sound cannot be found
            MissingPermissions:
                if calling user lacks permissions
        """
        if not (is_admin(member) or self.bot.is_bot_admin(member)):
            raise commands.MissingPermissions
        if name not in self.sounds(guild):
            raise SoundNotFoundException(f'Unable to find sound {name}')
        self.db.clear(guild, name)

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
        ignore_extra=False,
    )
    async def _join(self, ctx: commands.Context) -> bool:
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await self.bot.message_guild(
                '{}, you must be in a voice channel'.format(
                    ctx.author.mention
                ),
                ctx.channel,
            )
        else:
            await self.join_channel(ctx.author.voice.channel)

    @commands.command(
        name='leave',
        pass_context=True,
        brief='leave voice channel',
        ignore_extra=False,
    )
    async def _leave(self, ctx: commands.Context) -> None:
        await self.leave_channel(ctx.guild)

    @commands.group(
        name='sounds', pass_context=True, brief='?help sounds for more info'
    )
    async def _sounds(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self._list(ctx)

    @_sounds.command(
        name='add',
        pass_context=True,
        brief='add a sound: <name> <url> [image_url] [tag]',
        ignore_extra=False,
    )
    async def _add(
        self,
        ctx: commands.Context,
        name: str,
        url: str,
        image_url: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> None:
        try:
            self.add(ctx.guild, name, url, image_url=image_url, tag=tag)
        except SoundExistsException:
            await self.bot.message_guild(
                f'sound with name `{name}` already exists', ctx.channel
            )
        except SoundExceedsLimitException:
            await self.bot.message_guild(
                f'{ctx.author.mention}, the clip is too long '
                f'(max={MAX_SOUND_LENGTH_SECONDS}s)',
                ctx.channel,
            )
        except SoundDownloadException:
            await self.bot.message_guild(
                f'error downloading video for `{name}`', ctx.channel
            )
        else:
            await self.bot.message_guild(f'added sound `{name}`', ctx.channel)

    @_sounds.command(
        name='update',
        pass_context=True,
        brief='update a sound: <name> <key> <value>',
        ignore_extra=False,
    )
    async def _update(
        self, ctx: commands.Context, name: str, key: str, value: str
    ) -> None:
        sounds = self.sounds(ctx.guild)
        if name not in sounds:
            await self.bot.message_guild(
                f'sound with name `{name}` does not exists', ctx.channel
            )
            return
        if key not in sounds[name]:
            await self.bot.message_guild(
                f'`{key}` is not a valid option. Options are: '
                f'`{list(sounds[name].keys())}`',
                ctx.channel,
            )
            return
        kwargs = {key: value}
        try:
            self.update(ctx.guild, name, **kwargs)
        except SoundNotFoundException:
            await self.bot.message_guild(
                f'sound with name `{name}` does not exists', ctx.channel
            )
        except SoundExceedsLimitException:
            await self.bot.message_guild(
                f'{ctx.author.mention}, the new clip is too long '
                f'(max={MAX_SOUND_LENGTH_SECONDS}s)',
                ctx.channel,
            )
        except SoundDownloadException:
            await self.bot.message_guild(
                f'error downloading video for `{name}`', ctx.channel
            )
        else:
            await self.bot.message_guild(f'update sound `{name}`', ctx.channel)

    @_sounds.command(
        name='get',
        pass_context=True,
        brief='get sound data: <name>',
        ignore_extra=False,
    )
    async def _get(self, ctx: commands.Context, name: str) -> None:
        sounds = self.sounds(ctx.guild)
        if name in sounds:
            await self.bot.message_guild(
                f'`{name}`: `{sounds[name]}`', ctx.channel
            )
        else:
            await self.bot.message_guild(
                f'sound with name `{name}` does not exists', ctx.channel
            )

    @_sounds.command(
        name='remove',
        pass_context=True,
        brief='remove a sound: <name>',
        ignore_extra=False,
    )
    async def _remove(self, ctx: commands.Context, name: str) -> None:
        try:
            self.remove(ctx.guild, ctx.author, name)
        except commands.MissingPermissions:
            await self.bot.message_guild(
                f'{ctx.author.mention}, you lack permissions', ctx.channel
            )
        except SoundNotFoundException:
            await self.bot.message_guild(
                f'sound with name `{name}` does not exists', ctx.channel
            )
        else:
            await self.bot.message_guild(
                f'removed sound `{name}`', ctx.channel
            )

    async def _list(self, ctx: commands.Context) -> None:
        sounds = self.sounds(ctx.guild)
        sounds = ' '.join(sorted(sounds.keys()))
        await self.bot.message_guild(
            f'the available sounds are: `{sounds}`', ctx.channel
        )

    @_sounds.command(
        name='play',
        pass_context=True,
        brief='play a sound: [name]',
        ignore_extra=False,
    )
    async def _play(self, ctx: commands.Context, sound: str) -> None:
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await self.bot.message_guild(
                '{}, you must be in a voice channel'.format(
                    ctx.author.mention
                ),
                ctx.channel,
            )
        try:
            await self.play(ctx.author.voice.channel, sound)
        except JoinVoiceChannelException:
            await self.bot.message_guild(
                'failed to join the voice channel', ctx.channel
            )
        except SoundNotFoundException:
            await self.bot.message_guild(
                f'unable to find sound `{sound}`', ctx.channel
            )
        except Exception:
            logger.exception(
                f'Failed to play sound {sound} in guild {ctx.guild.id}'
            )

    @_sounds.command(
        name='roll',
        pass_context=True,
        brief='play a random sound',
        ignore_extra=False,
    )
    async def _roll(self, ctx: commands.Context) -> None:
        sounds = list(self.sounds(ctx.guild).keys())
        if len(sounds) < 1:
            await self.bot.message_guild(
                'there are no sounds available', ctx.channel
            )
        else:
            await self._play(ctx, random.choice(sounds))
