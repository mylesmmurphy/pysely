from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class IdentifierNode:
    name: str


@dataclass(frozen=True, slots=True)
class TableNode:
    name: IdentifierNode
    schema: IdentifierNode | None = None
    alias: IdentifierNode | None = None


@dataclass(frozen=True, slots=True)
class ReferenceNode:
    column: IdentifierNode
    table: tuple[IdentifierNode, ...] = ()


@dataclass(frozen=True, slots=True)
class ValueNode:
    value: object


@dataclass(frozen=True, slots=True)
class AliasNode:
    node: OperationNode
    alias: IdentifierNode


@dataclass(frozen=True, slots=True)
class BinaryOperationNode:
    left: OperationNode
    operator: str
    right: OperationNode


@dataclass(frozen=True, slots=True)
class IsNullNode:
    expression: OperationNode
    negated: bool = False


@dataclass(frozen=True, slots=True)
class AndNode:
    expressions: tuple[OperationNode, ...]


@dataclass(frozen=True, slots=True)
class SelectAllNode:
    table: tuple[IdentifierNode, ...] = ()


@dataclass(frozen=True, slots=True)
class SelectQueryNode:
    from_: tuple[TableNode, ...] = ()
    selections: tuple[OperationNode, ...] = ()
    where: OperationNode | None = None


OperationNode: TypeAlias = (
    IdentifierNode
    | TableNode
    | ReferenceNode
    | ValueNode
    | AliasNode
    | BinaryOperationNode
    | IsNullNode
    | AndNode
    | SelectAllNode
    | SelectQueryNode
)
