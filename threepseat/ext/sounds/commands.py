from __future__ import annotations

import asyncio
import datetime
import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.ext.extension import MAX_CHOICES_LENGTH
from threepseat.ext.extension import CommandGroupExtension
from threepseat.ext.sounds.data import MAX_SOUND_LENGTH_SECONDS
from threepseat.ext.sounds.data import MAX_SOUND_NAME_CHARS
from threepseat.ext.sounds.data import MemberSound
from threepseat.ext.sounds.data import MemberSoundTable
from threepseat.ext.sounds.data import Sound
from threepseat.ext.sounds.data import SoundsTable
from threepseat.ext.sounds.data import download
from threepseat.ext.sounds.data import remove_if_exists
from threepseat.ext.sounds.data import save_upload
from threepseat.ext.sounds.data import validate_upload_extension
from threepseat.ext.sounds.data import validate_upload_size
from threepseat.utils import LoopType
from threepseat.utils import leave_on_empty
from threepseat.utils import play_sound
from threepseat.utils import voice_channel

logger = logging.getLogger(__name__)


class SoundCommands(CommandGroupExtension):
    """App commands for sound board."""

    def __init__(self, db_path: str, data_path: str) -> None:
        """Init SoundCommands.

        Args:
            db_path (str): path to database to add table to.
            data_path (str): directory where sound files are stored.
        """
        self.table = SoundsTable(db_path, data_path)
        self.join_table = MemberSoundTable(db_path)
        self._vc_leaver_task: LoopType | None = None

        super().__init__(
            name='sounds',
            description='Soundboard for voice channels',
            guild_only=True,
        )

    async def post_init(self, bot: discord.ext.commands.Bot) -> None:
        """Spawn task that leaves channels when they are empty."""
        self._vc_leaver_task = leave_on_empty(bot, 60)
        self._vc_leaver_task.start()

        bot.add_listener(self.on_voice_state_update, 'on_voice_state_update')

    async def post_shutdown(self) -> None:
        """Cancel the voice channel leaver task and close the databases."""
        if self._vc_leaver_task is not None:
            self._vc_leaver_task.cancel()
            self._vc_leaver_task = None
        self.table.close()
        self.join_table.close()

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Play sounds on member voice channel join."""
        assert member.guild is not None
        if (
            not isinstance(after.channel, discord.VoiceChannel)
            or before.channel == after.channel
        ):
            return

        member_sound = self.join_table.get(
            member_id=member.id,
            guild_id=member.guild.id,
        )
        if member_sound is None:
            return

        sound = self.table.get(
            name=member_sound.name,
            guild_id=member.guild.id,
        )
        if sound is None:
            return

        try:
            await play_sound(
                self.table.filepath(sound.filename),
                after.channel,
            )
        except Exception:
            logger.exception(
                'caught exception when playing sound on member join',
            )

    @app_commands.command(
        name='add',
        description='Add a sound',
    )
    @app_commands.describe(
        name=f'Name of sound (max {MAX_SOUND_NAME_CHARS} characters)',
    )
    @app_commands.describe(link='Link to YouTube clip (max 30 seconds)')
    @app_commands.describe(
        description='Sound description (max 100 characters)',
    )
    @app_commands.check(log_interaction)
    async def add(
        self,
        interaction: discord.Interaction[commands.Bot],
        name: app_commands.Range[str, 1, MAX_SOUND_NAME_CHARS],
        link: str,
        description: app_commands.Range[str, 1, 100],
    ) -> None:
        """Add a new sound."""
        await interaction.response.defer(thinking=True)
        assert interaction.guild is not None

        existing = self.table.get(name=name, guild_id=interaction.guild.id)
        if existing is not None:
            message = f'A sound named {name} already exists.'
            await interaction.followup.send(message, ephemeral=True)
            return

        try:
            sound = Sound.new(
                name=name,
                description=description,
                link=link,
                author_id=interaction.user.id,
                guild_id=interaction.guild.id,
            )
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        assert sound.link is not None
        filepath = self.table.filepath(sound.filename)

        try:
            await asyncio.to_thread(download, sound.link, filepath)
            self.table.add(sound)
        except ValueError as e:
            await interaction.followup.send(str(e), ephemeral=True)
        else:
            await interaction.followup.send(f'Added *{name}* to the sounds.')

    async def autocomplete(
        self,
        interaction: discord.Interaction[commands.Bot],
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Return list of sound choices matching current."""
        assert interaction.guild is not None
        choices = [
            app_commands.Choice(name=sound.name, value=sound.name)
            for sound in self.table.all(interaction.guild.id)
            if current.lower() in sound.name.lower() or current == ''
        ]
        choices = sorted(choices, key=lambda c: c.name.lower())
        return choices[: min(len(choices), MAX_CHOICES_LENGTH)]

    @app_commands.command(
        name='list',
        description='List available sounds',
    )
    @app_commands.check(log_interaction)
    async def list(
        self,
        interaction: discord.Interaction[commands.Bot],
    ) -> None:
        """List available sounds."""
        await interaction.response.defer(thinking=True)
        assert interaction.guild is not None
        sounds = self.table.all(interaction.guild.id)

        if len(sounds) == 0:
            await interaction.followup.send('The guild has no sounds yet!')
        else:
            sounds_str = ', '.join([s.name for s in sounds])
            await interaction.followup.send(f'Available sounds: {sounds_str}')

    @app_commands.command(
        name='info',
        description='Information about a sound',
    )
    @app_commands.describe(name='Name of sound to query')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(log_interaction)
    async def info(
        self,
        interaction: discord.Interaction[commands.Bot],
        name: str,
    ) -> None:
        """Information about a sound."""
        assert interaction.guild is not None
        sound = self.table.get(name, guild_id=interaction.guild.id)
        if sound is None:
            await interaction.response.send_message(
                f'A sound named *{name}* does not exist.',
                ephemeral=True,
            )
        else:
            user = interaction.client.get_user(sound.author_id)
            user_str = user.mention if user is not None else 'unknown'
            date = datetime.datetime.fromtimestamp(
                sound.created_time,
                tz=datetime.UTC,
            ).strftime('%B %d, %Y')
            msg = f'**{sound.name}**: *{sound.description}*\n\n'
            msg += f'Added by {user_str} on {date}\n\n'
            msg += (
                f'{sound.link}'
                if len(sound.link) > 0
                else '*User uploaded file*'
            )
            await interaction.response.send_message(msg)

    @app_commands.command(
        name='play',
        description='Play a sound',
    )
    @app_commands.describe(name='Name of sound to play')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(log_interaction)
    async def play(
        self,
        interaction: discord.Interaction[commands.Bot],
        name: str,
    ) -> None:
        """Play a sound."""
        assert interaction.guild is not None
        sound = self.table.get(name, guild_id=interaction.guild.id)
        if sound is None:
            await interaction.response.send_message(
                f'A sound named *{name}* does not exist.',
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True, ephemeral=True)

        assert isinstance(interaction.user, discord.Member)
        channel = voice_channel(interaction.user)
        if channel is None:
            await interaction.followup.send(
                'You must be in a voice channel to play a sound.',
            )
            return

        try:
            await play_sound(self.table.filepath(sound.filename), channel)
        except Exception:
            await interaction.followup.send(
                'Failed to play the sound. Sorry.',
            )
            logger.exception('caught exception when playing sound')
        else:
            await interaction.followup.send('Played!')

    @app_commands.command(
        name='register',
        description='Register your entry sound',
    )
    @app_commands.describe(name='Name of sound to play when joining a channel')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(log_interaction)
    async def register(
        self,
        interaction: discord.Interaction[commands.Bot],
        name: str,
    ) -> None:
        """Register your sound."""
        assert interaction.guild is not None

        sound = self.table.get(name, guild_id=interaction.guild.id)
        if sound is None:
            await interaction.response.send_message(
                f'A sound named *{name}* does not exist.',
                ephemeral=True,
            )
            return

        member_sound = MemberSound(
            member_id=interaction.user.id,
            guild_id=interaction.guild.id,
            name=name,
            updated_time=time.time(),
        )
        self.join_table.update(member_sound)
        await interaction.response.send_message(
            f'Updated your voice channel entry sound to *{name}*.',
            ephemeral=True,
        )

    @app_commands.command(
        name='remove',
        description='[Admin Only] Remove a sound',
    )
    @app_commands.describe(name='Name of sound to remove')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(admin_or_owner)
    @app_commands.check(log_interaction)
    async def remove(
        self,
        interaction: discord.Interaction[commands.Bot],
        name: str,
    ) -> None:
        """Remove a sound."""
        assert interaction.guild is not None
        sound = self.table.get(name, guild_id=interaction.guild.id)
        if sound is None:
            await interaction.response.send_message(
                f'A sound named *{name}* does not exist.',
                ephemeral=True,
            )
        else:
            self.table.remove(name, interaction.guild.id)
            await interaction.response.send_message(
                f'Removed the *{name}* sound.',
                ephemeral=True,
            )

    @app_commands.command(
        name='upload',
        description='Upload an MP3 or video sound file directly',
    )
    @app_commands.describe(
        file=(
            'MP3 or video file to upload '
            f'(max {MAX_SOUND_LENGTH_SECONDS} seconds)'
        ),
    )
    @app_commands.describe(
        name=f'Name of sound (max {MAX_SOUND_NAME_CHARS} characters)',
    )
    @app_commands.describe(
        description='Sound description (max 100 characters)',
    )
    @app_commands.check(log_interaction)
    async def upload(
        self,
        interaction: discord.Interaction[commands.Bot],
        file: discord.Attachment,
        name: app_commands.Range[str, 1, MAX_SOUND_NAME_CHARS],
        description: app_commands.Range[str, 1, 100],
    ) -> None:
        """Upload a new sound via an MP3 or video attachment."""
        await interaction.response.defer(thinking=True)
        assert interaction.guild is not None

        try:
            # Check the extension and the declared size before downloading
            # the attachment, then the name before it is used as a filename.
            ext = validate_upload_extension(file.filename)
            validate_upload_size(ext, file.size)
            sound = Sound.new(
                name=name,
                description=description,
                link=None,
                author_id=interaction.user.id,
                guild_id=interaction.guild.id,
            )
        except ValueError as e:
            await interaction.followup.send(f'Error: {e}', ephemeral=True)
            return

        filepath = self.table.filepath(sound.filename)

        try:
            content = await file.read()
            await save_upload(content, ext, filepath)
            self.table.add(sound)
        except ValueError as e:
            remove_if_exists(filepath)
            await interaction.followup.send(f'Error: {e}', ephemeral=True)
        except Exception:
            logger.exception('failed to save uploaded sound')
            remove_if_exists(filepath)
            await interaction.followup.send(
                'Error: Could not process the file.',
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f'Uploaded and added *{name}* to the sounds.',
            )
