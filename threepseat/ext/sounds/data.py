from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import time
import uuid
from typing import NamedTuple
from typing import Self

from yt_dlp import YoutubeDL

from threepseat.logging import log_timing
from threepseat.table import SQLTableInterface
from threepseat.utils import alphanumeric

MAX_SOUND_FILE_SIZE_BYTES = 1 * 1024 * 1024
MAX_VIDEO_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_SOUND_LENGTH_SECONDS = 30
MAX_SOUND_NAME_CHARS = 18
MAX_SOUND_DESCRIPTION_CHARS = 100
SUPPORTED_VIDEO_EXTENSIONS = frozenset({'.mp4', '.m4v', '.mov'})

logger = logging.getLogger(__name__)


def supported_video_extensions_str() -> str:
    """Human-readable list of supported video extensions (without dots)."""
    return ', '.join(
        sorted(ext.lstrip('.') for ext in SUPPORTED_VIDEO_EXTENSIONS),
    )


def validate_sound_name(name: str) -> None:
    """Check a user-supplied sound name.

    The name is interpolated into the sound's filename, so this must be
    called before anything is written to disk. Otherwise a name like
    '../../evil' would escape the sounds directory.

    Raises:
        ValueError:
            if the name contains non-alphanumeric characters or is not
            between 1 and MAX_SOUND_NAME_CHARS characters long.
    """
    if not alphanumeric(name):
        msg = 'Name must contain only alphanumeric characters.'
        raise ValueError(msg)
    if len(name) == 0 or len(name) > MAX_SOUND_NAME_CHARS:
        msg = (
            f'Name must be between 1 and {MAX_SOUND_NAME_CHARS} '
            'characters long.'
        )
        raise ValueError(msg)


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
        """Create a new sound.

        Raises:
            ValueError:
                if the name is not a valid sound name. Validating here means
                no caller can build a filename from an unchecked name.
        """
        validate_sound_name(name)
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
        pathlib.Path(self.data_path).mkdir(parents=True, exist_ok=True)
        return str(pathlib.Path(self.data_path) / filename)

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
            msg = 'Sound with that name already exists.'
            raise ValueError(msg)
        validate_sound_name(sound.name)
        filepath = self.filepath(sound.filename)
        if not pathlib.Path(filepath).is_file():
            msg = f'{filepath} does not exist.'
            raise ValueError(msg)

        self.update(sound)
        logger.info('added sound to database: %s', sound)

    def _all(self, guild_id: int) -> tuple[Sound, ...]:  # type: ignore[override]
        """List sounds in database."""
        return super()._all(guild_id=guild_id)

    def _get(self, name: str, guild_id: int) -> Sound | None:  # type: ignore[override]
        """Get sound in database."""
        return super()._get(name=name, guild_id=guild_id)

    def remove(self, name: str, guild_id: int) -> None:  # type: ignore[override]
        """Remove sound from database."""
        sound = self.get(name=name, guild_id=guild_id)

        if sound is not None:
            super().remove(name=name, guild_id=guild_id)
            filepath = self.filepath(sound.filename)
            pathlib.Path(filepath).unlink()

            logger.info(
                'removed sound from database: (name=%s, guild_id=%s)',
                name,
                guild_id,
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

    def _all(self, guild_id: int) -> tuple[MemberSound, ...]:  # type: ignore[override]
        """Get all member sounds in guild."""
        return super()._all(guild_id=guild_id)

    def _get(  # type: ignore[override]
        self,
        member_id: int,
        guild_id: int,
    ) -> MemberSound | None:
        """Get MemberSound for member."""
        return super()._get(member_id=member_id, guild_id=guild_id)

    def remove(self, member_id: int, guild_id: int) -> int:  # type: ignore[override]
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
            logger.exception('caught error extracting sound metadata')
            msg = 'Error extracting sound metadata.'
            raise ValueError(msg) from e

        # Livestreams and some link types have no duration, in which case we
        # cannot enforce the length limit.
        duration = metadata.get('duration')
        if duration is None:
            msg = 'Could not determine the length of the clip.'
            raise ValueError(msg)

        if int(duration) > MAX_SOUND_LENGTH_SECONDS:
            msg = f'Clip is longer than {MAX_SOUND_LENGTH_SECONDS} seconds.'
            raise ValueError(msg)

        try:
            # Network download plus an ffmpeg transcode; the slowest operation
            # the bot performs, so time it.
            with log_timing(logger, 'downloaded sound from %s', link):
                ydl.download([link])
        except Exception as e:
            logger.exception('caught error downloading sound')
            msg = 'Error downloading sound.'
            raise ValueError(msg) from e


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
    # communicate() drains both pipes while waiting; wait() alone deadlocks if
    # the child fills the OS pipe buffer before exiting.
    stdout_b, stderr_b = await proc.communicate()
    stdout = stdout_b.decode().strip()
    stderr = stderr_b.decode().strip()

    if proc.returncode != 0:
        message = (
            f'Get duration with ffprobe failed (exit code {proc.returncode}): '
            f'{" ".join(cmd)}'
        )
        if stderr != '':
            message += f'\nstdout:\n{stdout}\nstderr:\n{stderr}'
        raise RuntimeError(message)

    probe_data = json.loads(stdout)
    return float(probe_data['format']['duration'])


async def extract_audio(source_path: str, mp3_path: str) -> None:
    """Extract the audio track of a media file to an MP3.

    Args:
        source_path (str): path to the source media file (e.g. a video).
        mp3_path (str): path to write the extracted MP3 audio to.

    Raises:
        ValueError:
            if ffmpeg fails to extract the audio (e.g. the source has no
            audio track or is not decodable).
    """
    cmd = (
        'ffmpeg',
        '-y',
        '-i',
        source_path,
        '-vn',
        '-acodec',
        'libmp3lame',
        '-b:a',
        '128k',
        '-f',
        'mp3',
        mp3_path,
    )
    with log_timing(logger, 'extracted audio from %s', source_path):
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # See mp3_duration_seconds: communicate() avoids a pipe deadlock.
        _, stderr_b = await proc.communicate()

    if proc.returncode != 0:
        stderr = stderr_b.decode().strip()
        logger.error(
            'extract audio with ffmpeg failed (exit code %s):\nstderr:\n%s',
            proc.returncode,
            stderr,
        )
        msg = 'Could not extract audio from the video.'
        raise ValueError(msg)
