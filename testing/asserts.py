from __future__ import annotations

from testing.mock import MockInteraction


def assert_responded(interaction: MockInteraction, contains: str = '') -> str:
    """Assert the interaction was responded to and return the message."""
    assert interaction.responded
    assert interaction.response_message is not None
    assert contains in interaction.response_message
    return interaction.response_message


def assert_followed(interaction: MockInteraction, contains: str = '') -> str:
    """Assert the interaction was deferred and return the followup message."""
    assert interaction.followed
    assert interaction.followup_message is not None
    assert contains in interaction.followup_message
    return interaction.followup_message
