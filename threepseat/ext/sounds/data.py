from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import time
import uuid
from typing import NamedTuple
from typing import Self

from yt_dlp import YoutubeDL

from threepseat.table import SQLTableInterface
from threepseat.utils import alphanumeric

MAX_SOUND_FILE_SIZE_BYTES = 1 * 1024 * 1024
MAX_SOUND_LENGTH_SECONDS = 30
MAX_SOUND_NAME_CHARS = 18
MAX_SOUND_DESCRIPTION_CHARS = 100

logger = logging.getLogger(__name__)


class Sound(NamedTuple):
    """Representation of entry in sounds database."""

    uuid: str
    name: str
    description: str
    link: str
    author_id: int
    guild_id: int
    created_time: float
    filename: str

    @classmethod
    def new(
        cls,
        name: str,
        description: str,
        link: str | None,
        author_id: int,
        guild_id: int,
    ) -> Self:
        """Create a new sound."""
        uuid_ = uuid.uuid4()
        return cls(
            uuid=str(uuid_),
            name=name,
            description=description,
            link=link if link is not None else '',
            author_id=author_id,
            guild_id=guild_id,
            created_time=time.time(),
            filename=f'{uuid_}-{name}-{guild_id}.mp3',
        )


class SoundsTable(SQLTableInterface[Sound]):
    """Sounds table interface."""

    def __init__(self, db_path: str, data_path: str) -> None:
        """Init SoundsTable.

        Args:
            db_path (str): path to sqlite database.
            data_path (str): directory where sound files are stored.
        """
        self.data_path = data_path

        super().__init__(
            Sound,
            'sounds',
            db_path,
            primary_keys=('name', 'guild_id'),
        )

    def filepath(self, filename: str) -> str:
        """Get filepath for filename."""
        os.makedirs(self.data_path, exist_ok=True)
        return os.path.join(self.data_path, filename)

    def add(self, sound: Sound) -> None:
        """Add sound to database.

        Raises:
            ValueError:
                if name contains non-alphanumeric characters.
            ValueError:
                if name is an invalid length.
            ValueError:
                if the filepath does not exist in the data directory.
            ValueError:
                if the name already exists.
            ValueError:
                any additional errors raises by download().
        """
        if self.get(name=sound.name, guild_id=sound.guild_id) is not None:
            raise ValueError('Sound with that name already exists.')
        if not alphanumeric(sound.name):
            raise ValueError('Name must contain only alphanumeric characters.')
        if len(sound.name) == 0 or len(sound.name) > MAX_SOUND_NAME_CHARS:
            raise ValueError('Name must be between 1 and 15 characters long.')
        filepath = self.filepath(sound.filename)
        if not os.path.isfile(filepath):
            raise ValueError(f'{filepath} does not exist.')

        self.update(sound)
        logger.info(f'added sound to database: {sound}')

    def _all(self, guild_id: int) -> list[Sound]:  # type: ignore
        """List sounds in database."""
        return super()._all(guild_id=guild_id)

    def _get(self, name: str, guild_id: int) -> Sound | None:  # type: ignore
        """Get sound in database."""
        return super()._get(name=name, guild_id=guild_id)

    def remove(self, name: str, guild_id: int) -> None:  # type: ignore
        """Remove sound from database."""
        sound = self.get(name=name, guild_id=guild_id)

        if sound is not None:
            super().remove(name=name, guild_id=guild_id)
            filepath = self.filepath(sound.filename)
            os.remove(filepath)

            logger.info(
                'removed sound from database: '
                f'(name={name}, guild_id={guild_id})',
            )


class MemberSound(NamedTuple):
    """Sound to play when a member joins a voice channel."""

    member_id: int
    guild_id: int
    name: str
    updated_time: float


class MemberSoundTable(SQLTableInterface[MemberSound]):
    """Sounds to play when members join voice channels."""

    def __init__(self, db_path: str) -> None:
        """Init MemberSoundTable.

        Args:
            db_path (str): path to sqlite database.
        """
        super().__init__(
            MemberSound,
            'member_sounds',
            db_path,
            primary_keys=('member_id', 'guild_id'),
        )

    def _all(self, guild_id: int) -> list[MemberSound]:  # type: ignore
        """Get all member sounds in guild."""
        return super()._all(guild_id=guild_id)

    def _get(  # type: ignore
        self,
        member_id: int,
        guild_id: int,
    ) -> MemberSound | None:
        """Get MemberSound for member."""
        return super()._get(member_id=member_id, guild_id=guild_id)

    def remove(self, member_id: int, guild_id: int) -> int:  # type: ignore
        """Remove a MemberSound from the table."""
        return super().remove(member_id=member_id, guild_id=guild_id)


def download(link: str, filepath: str) -> None:
    """Download sound from YouTube.

    Args:
        link (str): youtube link to download.
        filepath (str): filepath for downloaded file.

    Raises:
        ValueError:
            if the clip is longer than MAX_SOUND_LENGTH_SECONDS.
        ValueError:
            if there is an error downloading the clip.
    """
    filepath = str(pathlib.Path(filepath).with_suffix('.%(ext)s'))
    ydl_opts = {
        'outtmpl': filepath,
        'format': 'worst',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            },
        ],
        'logger': logger,
        'socket_timeout': 30,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            metadata = ydl.extract_info(
                link,
                download=False,
                process=False,
            )
        except Exception as e:
            logger.exception(
                f'caught error extracting sound metadata: {e}',
            )
            raise ValueError('Error extracting sound metadata.') from e

        if int(metadata['duration']) > MAX_SOUND_LENGTH_SECONDS:
            raise ValueError(
                f'Clip is longer than {MAX_SOUND_LENGTH_SECONDS} seconds.',
            )

        try:
            ydl.download([link])
        except Exception as e:
            logger.exception(f'caught error downloading sound: {e}')
            raise ValueError('Error downloading sound.') from e


async def mp3_duration_seconds(filepath: str) -> float:
    """Get the duration of an MP3 file in seconds.

    Args:
        filepath (str): path to the MP3 file to probe.

    Returns:
        duration of the audio in seconds.

    Raises:
        RuntimeError:
            if ffprobe fails to process the file.
    """
    cmd = (
        'ffprobe',
        '-v',
        'quiet',
        '-print_format',
        'json',
        '-show_format',
        filepath,
    )
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()

    stdout, stderr = ('', '')
    if proc.stdout is not None:
        stdout = (await proc.stdout.read()).decode().strip()
    if proc.stderr is not None:
        stderr = (await proc.stderr.read()).decode().strip()

    if proc.returncode != 0:
        message = (
            f'Get duration with ffmpeg failed (exit code {proc.returncode}): '
            f'{" ".join(cmd)}'
        )
        if stderr != '':
            message += f'\nstdout:\n{stdout}\nstderr:\n{stderr}'
        raise RuntimeError(message)

    probe_data = json.loads(stdout)
    return float(probe_data['format']['duration'])
