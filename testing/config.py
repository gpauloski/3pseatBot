from __future__ import annotations

EXAMPLE_CONFIG = {
    'bot_token': '1234abc',
    'client_id': 1234,
    'client_secret': 'abcd',
    'redirect_uri': 'http://localhost:5001',
    'sounds_path': '/tmp/threepseat',
    'sqlite_database': ':memory:',
}

TEMPLATE_CONFIG = """\
{
    "bot_token": <str>,
    "client_id": <int>,
    "client_secret": <str>,
    "redirect_uri": <str>,
    "sounds_path": <str>,
    "sqlite_database": <str>,
    "sounds_port": 5001,
    "playing_title": "3pseat Simulator 2022"
}
"""
