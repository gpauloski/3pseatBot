from __future__ import annotations


class EventStartError(Exception):
    """Raises when an event cannot be started in a guild."""


class GuildNotConfiguredError(Exception):
    """Raised when an operation requires a guild config that does not exist."""


class MaxOffensesExceededError(Exception):
    """Raised when a user exceeds the max number of offenses in the guild."""
