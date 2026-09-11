from __future__ import annotations

from collections.abc import Iterator, Mapping


class Row(Mapping[str, object]):
    """An immutable result row addressed by output column name.

    Rows from a typed client are instances of the generated row class, which
    subclasses this and adds the per-key overloads. Those overloads reject
    unknown keys, which also means checkers do not see the row as a plain
    ``Mapping[str, ...]`` for ``dict(row)`` or ``**row``; use ``row.to_dict()``.
    """

    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, object]) -> None:
        self._data: dict[str, object] = dict(data)

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def to_dict(self) -> dict[str, object]:
        return dict(self._data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"
