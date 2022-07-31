from __future__ import annotations

import logging

import discord
from discord import app_commands

from threepseat.commands.commands import log_interaction
from threepseat.commands.commands import register_app_command
from threepseat.tts import Accent
from threepseat.tts import tts_as_mp3
from threepseat.utils import play_sound
from threepseat.utils import voice_channel


logger = logging.getLogger(__name__)


@register_app_command
@app_commands.command(description='Read message as TTS in voice channel')
@app_commands.describe(text='Text to convert to speech (max characters: 200)')
@app_commands.describe(accent='Optional regional accent to use')
@app_commands.describe(slow='Optionally read message slowly')
@app_commands.check(log_interaction)
@app_commands.guild_only()
async def tts(
    interaction: discord.Interaction,
    text: str,
    accent: Accent = Accent.UNITED_STATES,
    slow: bool = False,
) -> None:
    """Read message as TTS in voice channel."""
    assert interaction.guild is not None
    assert isinstance(interaction.user, discord.Member)

    if len(text) > 200:
        await interaction.response.send_message(
            'Text length is limited to 200 characters.',
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True, ephemeral=True)
    channel = voice_channel(interaction.user)
    if channel is None:
        await interaction.followup.send(
            'You must be in a voice channel to use TTS.',
        )
        return

    try:
        with tts_as_mp3(text, accent=accent, slow=slow) as fp:
            await play_sound(fp, channel, wait=True)
    except Exception as e:
        await interaction.followup.send('Failed to play TTS.')
        logger.exception(f'caught exception playing TTS: {e}')
    else:
        await interaction.followup.send('Played TTS!')
