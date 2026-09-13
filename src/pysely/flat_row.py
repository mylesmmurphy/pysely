"""Runtime rows for stub-generated schemas; positional types live in the stub."""

from collections.abc import Iterator, Mapping
from typing import Generic, TypeVar, TypeVarTuple

K = TypeVar("K", bound=str)
V = TypeVar("V")
StarT = TypeVar("StarT", bound=str)
FieldsT = TypeVarTuple("FieldsT")


class Field(Generic[K, V]):
    """A type-only output key/value pair."""


class FlatRow(Mapping[str, object], Generic[StarT, *FieldsT]):
    """Immutable mapping whose generated interface tracks flat selected fields."""

    def __init__(self, data: Mapping[str, object]) -> None:
        self._data = dict(data)

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def to_dict(self) -> dict[str, object]:
        return dict(self._data)

    def __repr__(self) -> str:
        return f"FlatRow({self._data!r})"
