from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import get_type_hints

from pysely.errors import InvalidQueryError
from pysely.operation_node import (
    AliasNode,
    BinaryOperationNode,
    IdentifierNode,
    IsNullNode,
    OperationNode,
    ReferenceNode,
    TableNode,
    ValueNode,
)


def split_alias(value: str) -> tuple[str, str]:
    name, separator, alias = value.partition(" as ")
    return name, alias if separator else name


def table_node(value: str) -> TableNode:
    name, alias = split_alias(value)
    parts = name.split(".")
    return TableNode(
        IdentifierNode(parts[-1]),
        IdentifierNode(".".join(parts[:-1])) if len(parts) > 1 else None,
        IdentifierNode(alias) if alias != name else None,
    )


@dataclass(frozen=True)
class Schema:
    tables: dict[str, dict[str, object]]

    @classmethod
    def from_type(cls, database: type[object]) -> Schema:
        return cls(
            {
                name: get_type_hints(row)
                for name, row in get_type_hints(database).items()
            }
        )

    def add_table(self, scope: dict[str, str], value: str) -> dict[str, str]:
        name, alias = split_alias(value)
        if name not in self.tables:
            raise InvalidQueryError(f"Unknown table: {name}")
        if alias in scope:
            raise InvalidQueryError(f"Duplicate table alias: {alias}")
        return {**scope, alias: name}

    def reference(self, scope: dict[str, str], value: str) -> ReferenceNode:
        parts = value.rsplit(".", 1)
        column = parts[-1]
        candidates = [
            alias
            for alias, table in scope.items()
            if column in self.tables[table] and (len(parts) == 1 or alias == parts[0])
        ]
        if not candidates:
            raise InvalidQueryError(f"Unknown column in query scope: {value}")
        if len(candidates) > 1:
            raise InvalidQueryError(
                f"Ambiguous column: {value}; qualify it with a table"
            )
        return ReferenceNode(
            IdentifierNode(column),
            tuple(IdentifierNode(part) for part in parts[0].split("."))
            if len(parts) == 2
            else (),
        )

    def selection(self, scope: dict[str, str], value: str) -> ReferenceNode | AliasNode:
        name, alias = split_alias(value)
        node = self.reference(scope, name)
        return AliasNode(node, IdentifierNode(alias)) if alias != name else node

    def aliased_selection(
        self, scope: dict[str, str], source: str, alias: str
    ) -> AliasNode:
        return AliasNode(self.reference(scope, source), IdentifierNode(alias))

    def predicate(
        self, scope: dict[str, str], column: str, operator: str, value: object
    ) -> OperationNode:
        if operator not in {
            "=",
            "!=",
            "<>",
            "<",
            "<=",
            ">",
            ">=",
            "is",
            "is not",
            "like",
            "not like",
        }:
            raise InvalidQueryError(f"Unsupported comparison operator: {operator}")
        reference = self.reference(scope, column)
        if value is None and operator in {"is", "is not"}:
            return IsNullNode(reference, negated=operator == "is not")
        return BinaryOperationNode(reference, operator, ValueNode(value))

    def validate_values(self, table: str, values: Mapping[str, object]) -> None:
        unknown = values.keys() - self.tables[table].keys()
        if unknown:
            names = ", ".join(sorted(unknown))
            raise InvalidQueryError(f"Unknown column for {table}: {names}")
