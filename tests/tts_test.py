from __future__ import annotations

import os
from unittest import mock

import pytest

from threepseat.tts import Accent
from threepseat.tts import tts_as_mp3


def test_accent_from_str() -> None:
    assert Accent.from_str('AUSTRALIA') == Accent.AUSTRALIA

    with pytest.raises(KeyError):
        Accent.from_str('SOKOVIA')

    assert isinstance(Accent.from_str('', random_if_unknown=True), Accent)


def test_tts_as_mp3() -> None:
    with mock.patch('threepseat.tts.gTTS'):
        with tts_as_mp3('test message') as fp:
            filepath = fp
            assert os.path.isfile(fp)
        # File gets cleaned up
        assert not os.path.isfile(filepath)
