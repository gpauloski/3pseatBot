from __future__ import annotations

import datetime
import functools
import logging

import discord
from discord import app_commands

from threepseat.commands.commands import admin_or_owner
from threepseat.commands.commands import log_interaction
from threepseat.sounds.data import Sounds
from threepseat.utils import cached_load
from threepseat.utils import play_sound
from threepseat.utils import voice_channel

logger = logging.getLogger(__name__)


class SoundCommands(app_commands.Group):
    """App commands for sound board."""

    def __init__(self, sounds: Sounds) -> None:
        """Init SoundCommands.

        Args:
            sounds (Sounds): sounds database object.
        """
        self.sounds = sounds

        # Create a new cached list method because the function
        # can get called many times in quick succession for autocomplete
        self.sounds_list_cached = functools.lru_cache(maxsize=8)(
            self.sounds.list,
        )

        super().__init__(
            name='sounds',
            description='Soundboard for voice channels',
            guild_only=True,
        )

    @app_commands.command(name='add', description='Add a sound')
    @app_commands.describe(name='Name of sound (max 12 characters)')
    @app_commands.describe(link='Link to YouTube clip (max 30 seconds)')
    @app_commands.describe(
        description='Sound description (max 100 characters)',
    )
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        link: str,
        description: str,
    ) -> None:
        """Add a new sound."""
        log_interaction(interaction)

        await interaction.response.defer(thinking=True)

        assert interaction.guild is not None
        try:
            self.sounds.add(
                name=name,
                description=description,
                link=link,
                author_id=interaction.user.id,
                guild_id=interaction.guild.id,
            )
        except ValueError as e:
            await interaction.followup.send(str(e))
        else:
            self.sounds_list_cached.cache_clear()
            await interaction.followup.send(f'Added *{name}* to the sounds.')

    async def autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Return list of sound choices matching current."""
        assert interaction.guild is not None
        sounds = self.sounds_list_cached(interaction.guild.id)
        return [
            app_commands.Choice(name=sound.name, value=sound.name)
            for sound in sounds
            if current.lower() in sound.name.lower()
        ]

    @app_commands.command(name='list', description='List available sounds')
    async def list(self, interaction: discord.Interaction) -> None:
        """List available sounds."""
        log_interaction(interaction)

        await interaction.response.defer(thinking=True)
        assert interaction.guild is not None
        sounds = self.sounds.list(interaction.guild.id)

        if len(sounds) == 0:
            await interaction.followup.send('The guild has no sounds yet!')
        else:
            sounds_str = ', '.join([s.name for s in sounds])
            await interaction.followup.send(f'Available sounds: {sounds_str}')

    @app_commands.command(name='info', description='Information about a sound')
    @app_commands.describe(name='Name of sound to query')
    @app_commands.autocomplete(name=autocomplete)
    async def info(self, interaction: discord.Interaction, name: str) -> None:
        """Information about a sound."""
        log_interaction(interaction)

        assert interaction.guild is not None
        sound = self.sounds.get(name, guild_id=interaction.guild.id)
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
            ).strftime('%B %d, %Y')
            msg = f'**{sound.name}**: {sound.description}\n'
            msg += f'{sound.link}\n'
            msg += f'*Added by {user_str} on {date}*'
            await interaction.response.send_message(msg)

    @app_commands.command(name='play', description='Play a sound')
    @app_commands.describe(name='Name of sound to play')
    @app_commands.autocomplete(name=autocomplete)
    async def play(self, interaction: discord.Interaction, name: str) -> None:
        """Play a sound."""
        log_interaction(interaction)

        assert interaction.guild is not None
        sound = self.sounds.get(name, guild_id=interaction.guild.id)
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

        sound_data = cached_load(self.sounds.filepath(sound.filename))

        try:
            await play_sound(sound_data, channel)
        except Exception as e:
            await interaction.followup.send(
                'Failed to play the sound. Sorry.',
            )
            logger.exception(f'caught exception when playing sound: {e}')
        else:
            await interaction.followup.send('Played!')

    @app_commands.command(name='remove', description='Remove a sound')
    @app_commands.describe(name='Name of sound to remove')
    @app_commands.autocomplete(name=autocomplete)
    @app_commands.check(admin_or_owner)
    async def remove(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Remove a sound."""
        log_interaction(interaction)

        assert interaction.guild is not None
        self.sounds.remove(name, interaction.guild.id)
        self.sounds_list_cached.cache_clear()

        await interaction.response.send_message(
            f'Removed *{name}* if it existed.',
        )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        """Callback for errors in child functions."""
        log_interaction(interaction)
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(str(error), ephemeral=True)
            logger.info(f'app command check failed: {error}')
        else:
            logger.exception(error)
