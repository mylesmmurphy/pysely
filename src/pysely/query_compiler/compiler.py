from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from typing import Generic, TypeVar

from pysely.errors import InvalidQueryError, UnsupportedFeatureError
from pysely.operation_node import (
    AliasNode,
    AndNode,
    BinaryOperationNode,
    DeleteQueryNode,
    IdentifierNode,
    InsertQueryNode,
    IsNullNode,
    NotNode,
    OperationNode,
    OrderByItemNode,
    OrNode,
    ReferenceNode,
    RootOperationNode,
    SelectAllNode,
    SelectQueryNode,
    TableNode,
    UpdateQueryNode,
    ValueListNode,
    ValueNode,
)

RowT = TypeVar("RowT", covariant=True)


@dataclass(frozen=True, slots=True)
class BindingProfile:
    name: str
    placeholder: str
    identifier_open: str = '"'
    identifier_close: str = '"'
    returning_style: str | None = "returning"
    supports_right_join: bool = True
    supports_full_join: bool = True
    limit_style: str = "limit"
    """``limit``: ``limit n offset m``; ``fetch``: ``offset m rows fetch next``."""

    def bind(self, position: int) -> str:
        return self.placeholder.format(position=position)


@dataclass(frozen=True, slots=True)
class CompiledQuery(Generic[RowT]):
    sql: str
    parameters: tuple[object, ...]
    query: RootOperationNode
    query_id: str
    binding_profile: str


class QueryCompiler:
    def __init__(self, profile: BindingProfile) -> None:
        self.profile = profile
        self._parameters: list[object] = []

    def compile(
        self, node: RootOperationNode, query_id: str
    ) -> CompiledQuery[dict[str, object]]:
        """Compile a query.

        Bound parameters are collected while walking the tree, so each call
        works on its own copy. A single compiler is shared by every query on a
        client, and without this concurrent callers would interleave their
        parameter lists.
        """
        return copy(self)._compile_root(node, query_id)

    def _compile_root(
        self, node: RootOperationNode, query_id: str
    ) -> CompiledQuery[dict[str, object]]:
        self._parameters = []
        if isinstance(node, SelectQueryNode):
            sql = self._compile_select(node)
        elif isinstance(node, InsertQueryNode):
            sql = self._compile_insert(node)
        elif isinstance(node, UpdateQueryNode):
            sql = self._compile_update(node)
        else:
            sql = self._compile_delete(node)
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
        for join in node.joins:
            if join.kind == "right" and not self.profile.supports_right_join:
                raise UnsupportedFeatureError(
                    f"{self.profile.name} does not support right joins"
                )
            if join.kind == "full" and not self.profile.supports_full_join:
                raise UnsupportedFeatureError(
                    f"{self.profile.name} does not support full joins"
                )
            sql += (
                f" {join.kind} join {self._compile(join.table)}"
                f" on {self._compile(join.on)}"
            )
        if node.where:
            sql += " where " + self._compile(node.where)
        if node.group_by:
            sql += " group by " + ", ".join(self._compile(e) for e in node.group_by)
        if node.having:
            sql += " having " + self._compile(node.having)
        for operation in node.set_operations:
            sql += f" {operation.operator} {self._compile_select(operation.query)}"
        if node.order_by:
            sql += " order by " + ", ".join(
                f"{self._compile(item.expression)} {item.direction}"
                for item in node.order_by
            )
        sql += self._limit_clause(node)
        return sql

    def _limit_clause(self, node: SelectQueryNode) -> str:
        if node.limit is None and node.offset is None:
            return ""
        if self.profile.limit_style == "fetch":
            if not node.order_by:
                raise UnsupportedFeatureError(
                    f"{self.profile.name} requires order_by() with limit/offset"
                )
            sql = f" offset {self._bind(node.offset or 0)} rows"
            if node.limit is not None:
                sql += f" fetch next {self._bind(node.limit)} rows only"
            return sql
        sql = ""
        if node.limit is not None:
            sql += f" limit {self._bind(node.limit)}"
        if node.offset is not None:
            sql += f" offset {self._bind(node.offset)}"
        return sql

    def _bind(self, value: object) -> str:
        self._parameters.append(value)
        return self.profile.bind(len(self._parameters))

    def _compile_insert(self, node: InsertQueryNode) -> str:
        if not node.columns or not node.values:
            raise InvalidQueryError("insert values are required")
        if any(len(row) != len(node.columns) for row in node.values):
            raise InvalidQueryError("insert rows must contain the same columns")

        columns = ", ".join(self._compile(column) for column in node.columns)
        values = ", ".join(
            "(" + ", ".join(self._compile(value) for value in row) + ")"
            for row in node.values
        )
        sql = f"insert into {self._compile(node.into)} ({columns})"
        sql += self._output_clause(node.returning, "inserted")
        sql += f" values {values}"
        return sql + self._returning_clause(node.returning)

    def _compile_update(self, node: UpdateQueryNode) -> str:
        if not node.assignments:
            raise InvalidQueryError("update assignments are required")
        assignments = ", ".join(
            f"{self._compile(column)} = {self._compile(value)}"
            for column, value in node.assignments
        )
        sql = f"update {self._compile(node.table)} set {assignments}"
        sql += self._output_clause(node.returning, "inserted")
        if node.where:
            sql += " where " + self._compile(node.where)
        return sql + self._returning_clause(node.returning)

    def _compile_delete(self, node: DeleteQueryNode) -> str:
        sql = f"delete from {self._compile(node.from_)}"
        sql += self._output_clause(node.returning, "deleted")
        if node.where:
            sql += " where " + self._compile(node.where)
        return sql + self._returning_clause(node.returning)

    def _returning_clause(self, selections: tuple[OperationNode, ...]) -> str:
        if not selections:
            return ""
        if self.profile.returning_style is None:
            raise UnsupportedFeatureError(
                f"{self.profile.name} does not support returning projections"
            )
        if self.profile.returning_style == "output":
            return ""
        returning = ", ".join(
            self._compile_returning(selection) for selection in selections
        )
        return f" returning {returning}"

    def _output_clause(self, selections: tuple[OperationNode, ...], source: str) -> str:
        if not selections or self.profile.returning_style != "output":
            return ""
        output = ", ".join(
            self._compile_output(selection, source) for selection in selections
        )
        return f" output {output}"

    def _compile_returning(self, node: OperationNode) -> str:
        if isinstance(node, ReferenceNode):
            return self._compile(node.column)
        if isinstance(node, AliasNode):
            value = self._compile_returning(node.node)
            return f"{value} as {self._compile(node.alias)}"
        return self._compile(node)

    def _compile_output(self, node: OperationNode, source: str) -> str:
        if isinstance(node, ReferenceNode):
            return f"{self._quote(source)}.{self._compile(node.column)}"
        if isinstance(node, AliasNode):
            value = self._compile_output(node.node, source)
            return f"{value} as {self._compile(node.alias)}"
        return self._compile(node)

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
        if isinstance(node, ValueListNode):
            if not node.values:
                raise InvalidQueryError("in() requires at least one value")
            placeholders: list[str] = []
            for value in node.values:
                self._parameters.append(value)
                placeholders.append(self.profile.bind(len(self._parameters)))
            return "(" + ", ".join(placeholders) + ")"
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
        if isinstance(node, OrNode):
            expressions = " or ".join(self._compile(item) for item in node.expressions)
            return f"({expressions})"
        if isinstance(node, NotNode):
            return f"not ({self._compile(node.expression)})"
        if isinstance(node, SelectAllNode):
            if not node.table:
                return "*"
            table = ".".join(self._compile(part) for part in node.table)
            return f"{table}.*"
        if isinstance(node, SelectQueryNode):
            return f"({self._compile_select(node)})"
        if isinstance(node, OrderByItemNode):
            return f"{self._compile(node.expression)} {node.direction}"
        raise TypeError(f"Unsupported nested operation node: {type(node).__name__}")

    def _quote(self, identifier: str) -> str:
        escaped = identifier.replace(
            self.profile.identifier_close, self.profile.identifier_close * 2
        )
        return f"{self.profile.identifier_open}{escaped}{self.profile.identifier_close}"
