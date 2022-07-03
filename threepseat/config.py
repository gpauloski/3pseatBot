from __future__ import annotations

import dataclasses
import json
import typing


@dataclasses.dataclass(frozen=True, kw_only=True)
class Config:
    """3pseatBot configuration."""

    bot_token: str = dataclasses.field(repr=False)
    client_id: int
    client_secret: str = dataclasses.field(repr=False)
    mongodb_connection: str
    playing_title: str = '3pseat Simulator 2022'

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        for field_name, field_type in typing.get_type_hints(Config).items():
            value = getattr(self, field_name)
            if not isinstance(value, field_type):
                raise TypeError(
                    f'Expected type \'{field_type.__name__}\' for '
                    f'{self.__class__.__name__} field \'{field_name}\' but '
                    f'got type \'{type(value).__name__}\'.',
                )

    @staticmethod
    def template() -> str:
        """Returns JSON-like template for a config file."""
        fields: list[tuple[str, str]] = []
        for field in dataclasses.fields(Config):
            if field.default == dataclasses.MISSING:
                # types should always be strings because our type evaluation
                # is postponed due to "from __future__ import annotations"
                assert isinstance(field.type, str)
                value = f'<{field.type}>'
            elif isinstance(field.default, str):
                value = f'"{field.default}"'
            else:
                # Note: if this line is ever reached, it is because a new field
                # was added to Config with a default type not handled in this
                # if/elif statement so a new elif needs to be added.
                raise AssertionError('Unreachable.')
            fields.append((field.name, value))
        field_strs = [f'    "{f}": {t}' for f, t in fields]
        field_str = ',\n'.join(field_strs)
        return f'{{\n{field_str}\n}}\n'


def load(filepath: str) -> Config:
    """Load config from JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    return Config(**data)


def write_template(filepath: str) -> None:
    """Write config template to file."""
    with open(filepath, 'w') as f:
        f.write(Config.template())
