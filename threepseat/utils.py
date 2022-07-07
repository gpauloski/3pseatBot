from __future__ import annotations

import re


def alphanumeric(s: str) -> bool:
    """Check if string is alphanumeric characters only."""
    return len(re.findall(r'[^A-Za-z0-9]', s)) == 0
