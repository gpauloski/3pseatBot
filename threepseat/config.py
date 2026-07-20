from __future__ import annotations

import dataclasses
import json
import typing
from pathlib import Path


@dataclasses.dataclass(frozen=True, kw_only=True)
class Config:
    """3pseatBot configuration."""

    bot_token: str = dataclasses.field(repr=False)
    client_id: int
    client_secret: str = dataclasses.field(repr=False)
    secret_key: str | None = dataclasses.field(default=None, repr=False)
    redirect_uri: str
    sounds_path: str
    sqlite_database: str
    sounds_port: int = 5001
    sounds_certfile: str | None = None
    sounds_keyfile: str | None = None
    playing_title: str = '3pseat Simulator 2022'

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        for field_name, field_type in typing.get_type_hints(Config).items():
            value = getattr(self, field_name)
            if not isinstance(value, field_type):
                msg = (
                    f"Expected type '{field_type.__name__}' for "
                    f"{self.__class__.__name__} field '{field_name}' but "
                    f"got type '{type(value).__name__}'."
                )
                raise TypeError(msg)

    @staticmethod
    def template() -> str:
        """Returns JSON-like template for a config file.

        Required fields are rendered as unquoted `<type>` placeholders, so
        the result is deliberately not valid JSON until they are filled in.
        """
        fields: list[str] = []
        for field in dataclasses.fields(Config):
            if field.default is dataclasses.MISSING:
                # Types are strings because annotation evaluation is
                # postponed by "from __future__ import annotations".
                assert isinstance(field.type, str)
                value = f'<{field.type}>'
            else:
                # json.dumps renders any default in its JSON form, so new
                # fields need no changes here.
                value = json.dumps(field.default)
            fields.append(f'    "{field.name}": {value}')
        field_str = ',\n'.join(fields)
        return f'{{\n{field_str}\n}}\n'


def load(filepath: str) -> Config:
    """Load config from JSON file."""
    with Path(filepath).open() as f:
        data = json.load(f)

    return Config(**data)


def write_template(filepath: str) -> None:
    """Write config template to file."""
    with Path(filepath).open('w') as f:
        f.write(Config.template())
