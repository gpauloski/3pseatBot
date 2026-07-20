from __future__ import annotations

from threepseat.ext.reminders.data import Reminder
from threepseat.ext.rules.data import GuildConfig

GUILD_CONFIG = GuildConfig(
    guild_id=1234,
    enabled=1,
    event_expectancy=0.5,
    event_duration=24,
    event_cooldown=5.0,
    last_event=0,
    max_offenses=3,
    timeout_duration=300,
    prefixes='3pseat, 3pfeet',
)

REMINDER = Reminder(
    guild_id=1234,
    channel_id=5678,
    author_id=9012,
    creation_time=0,
    name='test',
    text='test message',
    delay_minutes=1,
)
