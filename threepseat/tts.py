from __future__ import annotations

import contextlib
import enum
import tempfile
from collections.abc import Generator

from gtts import gTTS


class Accent(enum.Enum):
    """TLDs for English Accents."""

    AUSTRALIA = 'com.au'
    UNITED_KINGDOM = 'co.uk'
    UNITED_STATES = 'com'
    CANADA = 'ca'
    INDIA = 'co.in'
    IRELAND = 'ie'
    SOUTH_AFRICA = 'co.za'


@contextlib.contextmanager
def tts_as_mp3(
    text: str,
    accent: Accent = Accent.UNITED_STATES,
    slow: bool = False,
) -> Generator[str, None, None]:
    """Yield temporary TTS MP3 file.

    Args:
        text (str): text to convert to speech.
        accent (Accent): regional English accent to use (default: US).
        slow (bool): read text slower (default: False).

    Yields:
        Filepath (str) to MP3 TTS file. The file is temporary and will be
        removed once the context is exited.
    """
    tts = gTTS(text, lang='en', tld=accent.value, slow=slow)
    print(tts.write_to_fp)
    with tempfile.NamedTemporaryFile() as fp:
        tts.write_to_fp(fp)
        yield fp.name
