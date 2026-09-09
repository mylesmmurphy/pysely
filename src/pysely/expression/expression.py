from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from pysely.operation_node import (
    AliasNode,
    BinaryOperationNode,
    IdentifierNode,
    IsNullNode,
    OperationNode,
    ValueNode,
)

T = TypeVar("T")


class OperationExpression(Protocol):
    @property
    def node(self) -> OperationNode: ...


@dataclass(frozen=True, slots=True)
class Expression(Generic[T]):
    node: OperationNode

    def __bool__(self) -> bool:
        raise TypeError(
            "SQL expressions cannot be used as Python booleans; use and_() or or_()"
        )

    def eq(self, value: T) -> Expression[bool]:
        if value is None:
            return Expression(IsNullNode(self.node))
        return Expression(BinaryOperationNode(self.node, "=", ValueNode(value)))

    def ne(self, value: T) -> Expression[bool]:
        if value is None:
            return Expression(IsNullNode(self.node, negated=True))
        return Expression(BinaryOperationNode(self.node, "!=", ValueNode(value)))

    def is_null(self) -> Expression[bool]:
        return Expression(IsNullNode(self.node))

    def is_not_null(self) -> Expression[bool]:
        return Expression(IsNullNode(self.node, negated=True))

    def as_(self, alias: str) -> AliasedExpression[T]:
        return AliasedExpression(AliasNode(self.node, IdentifierNode(alias)))


@dataclass(frozen=True, slots=True)
class AliasedExpression(Expression[T]):
    pass
