from __future__ import annotations

from threepseat.custom.data import CustomCommand
from threepseat.custom.data import CustomCommandTable


COMMAND = CustomCommand(
    name='mycommand',
    description='my test commands',
    body='my test command description',
    author_id=1234,
    guild_id=5678,
    creation_time=0,
)


def test_all_commands(tmp_file: str) -> None:
    table = CustomCommandTable(tmp_file)

    table.update(COMMAND)
    assert len(table.all()) == 1
    assert len(table.all(guild_id=COMMAND.guild_id)) == 1
    assert len(table.all(guild_id=42)) == 0


def test_get_commands(tmp_file: str) -> None:
    table = CustomCommandTable(tmp_file)

    assert table.get(1234, 'command') is None
    table.update(COMMAND)
    assert table.get(COMMAND.guild_id, COMMAND.name) == COMMAND


def test_remove_commands(tmp_file: str) -> None:
    table = CustomCommandTable(tmp_file)

    assert table.remove(1234, 'command') == 0
    table.update(COMMAND)
    assert table.remove(COMMAND.guild_id, COMMAND.name) == 1
    assert table.get(COMMAND.guild_id, COMMAND.name) is None
