from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar, get_args, get_origin, get_type_hints

from pysely.errors import InvalidQueryError
from pysely.operation_node import (
    AliasNode,
    BinaryOperationNode,
    IdentifierNode,
    IsNullNode,
    OperationNode,
    ReferenceNode,
    TableNode,
    ValueListNode,
    ValueNode,
)

COMPARISON_OPERATORS = frozenset({"=", "!=", "<>", "<", "<=", ">", ">="})
NULL_OPERATORS = frozenset({"is", "is not"})
PATTERN_OPERATORS = frozenset({"like", "not like"})
COLLECTION_OPERATORS = frozenset({"in", "not in"})

ClientT = TypeVar("ClientT")


class GeneratedSchema(Generic[ClientT]):
    """Base class `pysely codegen` gives a schema class.

    The type argument names the typed client for that schema, which is how
    `Database(schema=...)` knows what to build and what to return.
    """

    __pysely_client__: ClassVar[type[Any]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for base in getattr(cls, "__orig_bases__", ()):
            if get_origin(base) is GeneratedSchema:
                cls.__pysely_client__ = get_args(base)[0]


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
                if not name.startswith("_")
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

    def order_reference(
        self,
        scope: dict[str, str],
        selections: tuple[OperationNode, ...],
        value: str,
    ) -> OperationNode:
        """A column in scope, or the alias of a selection already made."""
        for node in selections:
            if isinstance(node, AliasNode) and node.alias.name == value:
                return IdentifierNode(value)
        return self.reference(scope, value)

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
        """Build ``column <operator> value``.

        Each operator family takes a different value shape, and the runtime
        enforces the same rules the generated overloads express: comparisons
        and patterns bind one non-null value, ``is``/``is not`` take ``None``,
        and ``in``/``not in`` take a non-string sequence.
        """
        reference = self.reference(scope, column)
        if operator in NULL_OPERATORS:
            if value is not None:
                raise InvalidQueryError(f"{operator!r} compares against None only")
            return IsNullNode(reference, negated=operator == "is not")
        if operator in COLLECTION_OPERATORS:
            if isinstance(value, str | bytes) or not isinstance(
                value, Sequence | AbstractSet
            ):
                raise InvalidQueryError(f"{operator!r} requires a list or tuple")
            return BinaryOperationNode(reference, operator, ValueListNode(tuple(value)))
        if operator in COMPARISON_OPERATORS or operator in PATTERN_OPERATORS:
            if value is None:
                raise InvalidQueryError(
                    f"{operator!r} cannot compare against None; use 'is' or 'is not'"
                )
            return BinaryOperationNode(reference, operator, ValueNode(value))
        raise InvalidQueryError(f"Unsupported comparison operator: {operator}")

    def validate_values(self, table: str, values: Mapping[str, object]) -> None:
        unknown = values.keys() - self.tables[table].keys()
        if unknown:
            names = ", ".join(sorted(unknown))
            raise InvalidQueryError(f"Unknown column for {table}: {names}")
