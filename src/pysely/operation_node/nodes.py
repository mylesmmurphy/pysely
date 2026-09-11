from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

JoinKind: TypeAlias = Literal["inner", "left", "right", "full"]


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
class ValueListNode:
    """A parenthesized list of bound values, as used by ``in``."""

    values: tuple[object, ...]


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
class OrNode:
    expressions: tuple[OperationNode, ...]


@dataclass(frozen=True, slots=True)
class NotNode:
    expression: OperationNode


@dataclass(frozen=True, slots=True)
class SelectAllNode:
    table: tuple[IdentifierNode, ...] = ()


@dataclass(frozen=True, slots=True)
class JoinNode:
    table: TableNode
    on: BinaryOperationNode
    kind: JoinKind = "inner"


@dataclass(frozen=True, slots=True)
class SelectQueryNode:
    from_: tuple[TableNode, ...] = ()
    selections: tuple[OperationNode, ...] = ()
    where: OperationNode | None = None
    joins: tuple[JoinNode, ...] = ()


@dataclass(frozen=True, slots=True)
class InsertQueryNode:
    into: TableNode
    columns: tuple[IdentifierNode, ...] = ()
    values: tuple[tuple[OperationNode, ...], ...] = ()
    returning: tuple[OperationNode, ...] = ()


@dataclass(frozen=True, slots=True)
class UpdateQueryNode:
    table: TableNode
    assignments: tuple[tuple[IdentifierNode, OperationNode], ...] = ()
    where: OperationNode | None = None
    returning: tuple[OperationNode, ...] = ()


@dataclass(frozen=True, slots=True)
class DeleteQueryNode:
    from_: TableNode
    where: OperationNode | None = None
    returning: tuple[OperationNode, ...] = ()


OperationNode: TypeAlias = (
    IdentifierNode
    | TableNode
    | ReferenceNode
    | ValueNode
    | ValueListNode
    | AliasNode
    | BinaryOperationNode
    | IsNullNode
    | AndNode
    | OrNode
    | NotNode
    | SelectAllNode
    | SelectQueryNode
    | JoinNode
    | InsertQueryNode
    | UpdateQueryNode
    | DeleteQueryNode
)

RootOperationNode: TypeAlias = (
    SelectQueryNode | InsertQueryNode | UpdateQueryNode | DeleteQueryNode
)
