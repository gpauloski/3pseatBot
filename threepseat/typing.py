from __future__ import annotations

import types
import typing


def base_type(t: types.UnionType) -> type:
    """Get the base type of an optional type annotation.

    For example, if a field has the type annotations `int | None`, this
    function will return int.

    Args:
        t (type): the optional field type to extract the base type from.

    Returns:
        the base type.

    Raises:
        ValueError:
            if the field is not optional or there are more than one "base"
            types.
    """
    types_ = split_types(t)
    if len(types_) == 2 and type(None) in types_:
        return [t for t in types_ if t is not type(None)].pop()  # noqa: E721
    raise ValueError(
        'Argument must contain two types with one of them being type[None] '
        f'but got {types_} instead.',
    )


def is_optional(t: types.UnionType) -> bool:
    """Check if the type is an optional type."""
    origin = typing.get_origin(t)
    union = origin is typing.Union or origin is types.UnionType  # noqa: E721
    return union and type(None) in typing.get_args(t)


def split_types(t: types.UnionType | type) -> tuple[type, ...]:
    """Splits a union type into a tuple of the sub-types."""
    if isinstance(t, types.UnionType):
        return typing.get_args(t)
    return (t,)
