from __future__ import annotations

import functools
import io
import re


def alphanumeric(s: str) -> bool:
    """Check if string is alphanumeric characters only."""
    return len(re.findall(r'[^A-Za-z0-9]', s)) == 0


@functools.lru_cache(maxsize=16)
def cached_load(filepath: str) -> io.BytesIO:
    """Load file as bytes (cached)."""
    with open(filepath, 'rb') as f:
        return io.BytesIO(f.read())
