from __future__ import annotations

EXAMPLE_CONFIG = {
    'bot_token': '1234abc',
    'client_id': 1234,
    'client_secret': 'abcd',
    'sqlite_database': ':memory:',
}

TEMPLATE_CONFIG = """\
{
    "bot_token": <str>,
    "client_id": <int>,
    "client_secret": <str>,
    "sqlite_database": <str>,
    "playing_title": "3pseat Simulator 2022"
}
"""
