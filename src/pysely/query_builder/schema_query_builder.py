from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Generic, TypeVar, cast
from uuid import uuid4

from pysely.errors import InvalidQueryError, NoResultError
from pysely.operation_node import (
    AndNode,
    BinaryOperationNode,
    IsNullNode,
    JoinNode,
    OperationNode,
    SelectQueryNode,
    ValueNode,
)
from pysely.query_compiler import CompiledQuery
from pysely.query_executor import QueryExecutor
from pysely.schema import Schema, table_node

DatabaseT = TypeVar("DatabaseT")
ScopeT = TypeVar("ScopeT")
RowT = TypeVar("RowT")


@dataclass(frozen=True)
class SchemaQueryBuilder(Generic[DatabaseT, ScopeT, RowT]):
    _node: SelectQueryNode
    _executor: QueryExecutor
    _schema: Schema
    _scope: dict[str, str]
    _query_id: str

    @classmethod
    def from_name(
        cls, name: str, executor: QueryExecutor, schema: Schema
    ) -> SchemaQueryBuilder[DatabaseT, object, dict[str, object]]:
        return SchemaQueryBuilder(
            SelectQueryNode(from_=(table_node(name),)),
            executor,
            schema,
            schema.add_table({}, name),
            uuid4().hex,
        )

    def select(
        self, selections: str | list[str] | tuple[str, ...]
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        names = (selections,) if isinstance(selections, str) else selections
        nodes = tuple(self._schema.selection(self._scope, name) for name in names)
        return replace(
            self, _node=replace(self._node, selections=(*self._node.selections, *nodes))
        )

    def where(
        self, column: str, operator: str, value: object
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
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
        reference = self._schema.reference(self._scope, column)
        predicate: OperationNode = BinaryOperationNode(
            reference, operator, ValueNode(value)
        )
        if value is None and operator in {"is", "is not"}:
            predicate = IsNullNode(reference, negated=operator == "is not")
        where = (
            AndNode((self._node.where, predicate)) if self._node.where else predicate
        )
        return replace(self, _node=replace(self._node, where=where))

    def inner_join(
        self, table: str, left: str, right: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        scope = self._schema.add_table(self._scope, table)
        on = BinaryOperationNode(
            self._schema.reference(scope, left),
            "=",
            self._schema.reference(scope, right),
        )
        join = JoinNode(table_node(table), on)
        return replace(
            self,
            _scope=scope,
            _node=replace(self._node, joins=(*self._node.joins, join)),
        )

    def compile(self) -> CompiledQuery[RowT]:
        return cast(
            CompiledQuery[RowT],
            self._executor.compile_query(self._node, self._query_id),
        )

    async def execute(self) -> list[RowT]:
        result = await self._executor.execute_query(self._node, self._query_id)
        return cast(list[RowT], list(result.rows))

    async def execute_take_first(self) -> RowT | None:
        rows = await self.execute()
        return rows[0] if rows else None

    async def execute_take_first_or_throw(self) -> RowT:
        row = await self.execute_take_first()
        if row is None:
            raise NoResultError("Query returned no rows")
        return row
