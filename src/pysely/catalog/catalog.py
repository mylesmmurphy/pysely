from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from pysely.expression import Expression
from pysely.operation_node import IdentifierNode, ReferenceNode, TableNode

ReadT = TypeVar("ReadT")
InsertT = TypeVar("InsertT")
UpdateT = TypeVar("UpdateT")
NameT = TypeVar("NameT", bound=str, covariant=True)
SourceT = TypeVar("SourceT", bound=str, covariant=True)
RowT = TypeVar("RowT")
ColumnsT = TypeVar("ColumnsT")


@dataclass(frozen=True, slots=True)
class Column(Expression[ReadT], Generic[ReadT, InsertT, UpdateT, NameT, SourceT]):
    name: NameT
    source: SourceT
    nullable: bool = False
    has_default: bool = False
    writable: bool = True

    def __init__(
        self,
        name: NameT,
        source: SourceT,
        *,
        nullable: bool = False,
        has_default: bool = False,
        writable: bool = True,
    ) -> None:
        source_parts = tuple(IdentifierNode(part) for part in source.split("."))
        object.__setattr__(
            self,
            "node",
            ReferenceNode(column=IdentifierNode(name), table=source_parts),
        )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "nullable", nullable)
        object.__setattr__(self, "has_default", has_default)
        object.__setattr__(self, "writable", writable)


class Table(Generic[RowT, InsertT, UpdateT, ColumnsT]):
    __slots__ = ("_columns_factory", "alias", "c", "name", "schema")

    def __init__(
        self,
        *,
        name: str,
        columns: ColumnsT,
        columns_factory: Callable[[str], ColumnsT],
        schema: str | None = None,
        alias: str | None = None,
    ) -> None:
        self.name = name
        self.schema = schema
        self.alias = alias
        self.c = columns
        self._columns_factory = columns_factory

    @property
    def source(self) -> str:
        return self.alias or ".".join(part for part in (self.schema, self.name) if part)

    def as_(self, alias: str) -> Table[RowT, InsertT, UpdateT, ColumnsT]:
        return Table(
            name=self.name,
            schema=self.schema,
            alias=alias,
            columns=self._columns_factory(alias),
            columns_factory=self._columns_factory,
        )

    def to_operation_node(self) -> TableNode:
        return TableNode(
            name=IdentifierNode(self.name),
            schema=IdentifierNode(self.schema) if self.schema else None,
            alias=IdentifierNode(self.alias) if self.alias else None,
        )
