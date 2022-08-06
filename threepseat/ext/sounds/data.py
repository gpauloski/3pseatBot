from __future__ import annotations

import logging
import os
import time
import uuid
from typing import NamedTuple

import youtube_dl

from threepseat.table import SQLTableInterface
from threepseat.utils import alphanumeric

MAX_SOUND_LENGTH_SECONDS = 30

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

    def add(
        self,
        name: str,
        description: str,
        link: str,
        author_id: int,
        guild_id: int,
    ) -> None:
        """Add sound to database.

        Raises:
            ValueError:
                if name contains non-alphanumeric characters.
            ValueError:
                if name is not between 1 and 12 characters long.
            ValueError:
                any additional errors raises by download().
        """
        if not alphanumeric(name):
            raise ValueError('Name must contain only alphanumeric characters.')
        if len(name) == 0 or len(name) > 12:
            raise ValueError('Name must be between 1 and 12 characters long.')

        existing = self.get(name=name, guild_id=guild_id)
        if existing is not None:
            raise ValueError('Sound with that name already exists.')

        uuid_ = uuid.uuid4()
        sound = Sound(
            uuid=str(uuid_),
            name=name,
            description=description,
            link=link,
            author_id=author_id,
            guild_id=guild_id,
            created_time=time.time(),
            filename=f'{uuid_}-{name}-{guild_id}.mp3',
        )

        download(sound.link, self.filepath(sound.filename))

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

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
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
            raise ValueError('Error extracting sound metadata.')

        if int(metadata['duration']) > MAX_SOUND_LENGTH_SECONDS:
            raise ValueError(
                f'Clip is longer than {MAX_SOUND_LENGTH_SECONDS} ' 'seconds.',
            )

        try:
            ydl.download([link])
        except Exception as e:
            logger.exception(f'caught error downloading sound: {e}')
            raise ValueError('Error downloading sound.')
