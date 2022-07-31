from __future__ import annotations

import os
from unittest import mock

from threepseat.tts import tts_as_mp3


def test_tts_as_mp3() -> None:
    with mock.patch('threepseat.tts.gTTS'):
        with tts_as_mp3('test message') as fp:
            filepath = fp
            assert os.path.isfile(fp)
        # File gets cleaned up
        assert not os.path.isfile(filepath)
