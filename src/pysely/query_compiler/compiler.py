from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from pysely.errors import InvalidQueryError
from pysely.operation_node import (
    AliasNode,
    AndNode,
    BinaryOperationNode,
    IdentifierNode,
    IsNullNode,
    OperationNode,
    ReferenceNode,
    SelectAllNode,
    SelectQueryNode,
    TableNode,
    ValueNode,
)

RowT = TypeVar("RowT", covariant=True)


@dataclass(frozen=True, slots=True)
class BindingProfile:
    name: str
    placeholder: str
    identifier_open: str = '"'
    identifier_close: str = '"'

    def bind(self, position: int) -> str:
        return self.placeholder.format(position=position)


@dataclass(frozen=True, slots=True)
class CompiledQuery(Generic[RowT]):
    sql: str
    parameters: tuple[object, ...]
    query: SelectQueryNode
    query_id: str
    binding_profile: str


class QueryCompiler:
    def __init__(self, profile: BindingProfile) -> None:
        self.profile = profile
        self._parameters: list[object] = []

    def compile(
        self, node: SelectQueryNode, query_id: str
    ) -> CompiledQuery[dict[str, object]]:
        self._parameters = []
        sql = self._compile_select(node)
        return CompiledQuery(
            sql=sql,
            parameters=tuple(self._parameters),
            query=node,
            query_id=query_id,
            binding_profile=self.profile.name,
        )

    def _compile_select(self, node: SelectQueryNode) -> str:
        if not node.selections:
            raise InvalidQueryError("select() or select_all() is required")

        sql = "select " + ", ".join(self._compile(item) for item in node.selections)
        if node.from_:
            sql += " from " + ", ".join(self._compile(table) for table in node.from_)
        if node.where:
            sql += " where " + self._compile(node.where)
        return sql

    def _compile(self, node: OperationNode) -> str:
        if isinstance(node, IdentifierNode):
            return self._quote(node.name)
        if isinstance(node, TableNode):
            parts = [node.name]
            if node.schema:
                parts.insert(0, node.schema)
            sql = ".".join(self._compile(part) for part in parts)
            if node.alias:
                sql += f" as {self._compile(node.alias)}"
            return sql
        if isinstance(node, ReferenceNode):
            parts = [*node.table, node.column]
            return ".".join(self._compile(part) for part in parts)
        if isinstance(node, ValueNode):
            self._parameters.append(node.value)
            return self.profile.bind(len(self._parameters))
        if isinstance(node, AliasNode):
            return f"{self._compile(node.node)} as {self._compile(node.alias)}"
        if isinstance(node, BinaryOperationNode):
            left = self._compile(node.left)
            right = self._compile(node.right)
            return f"{left} {node.operator} {right}"
        if isinstance(node, IsNullNode):
            operator = "is not null" if node.negated else "is null"
            return f"{self._compile(node.expression)} {operator}"
        if isinstance(node, AndNode):
            expressions = " and ".join(self._compile(item) for item in node.expressions)
            return f"({expressions})"
        if isinstance(node, SelectAllNode):
            if not node.table:
                return "*"
            table = ".".join(self._compile(part) for part in node.table)
            return f"{table}.*"
        return f"({self._compile_select(node)})"

    def _quote(self, identifier: str) -> str:
        escaped = identifier.replace(
            self.profile.identifier_close, self.profile.identifier_close * 2
        )
        return f"{self.profile.identifier_open}{escaped}{self.profile.identifier_close}"
