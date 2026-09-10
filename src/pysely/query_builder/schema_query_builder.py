from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Generic, Literal, Self, TypeAlias, TypeVar, cast
from uuid import uuid4

from pysely.errors import NoResultError
from pysely.operation_node import (
    AndNode,
    BinaryOperationNode,
    JoinNode,
    SelectQueryNode,
)
from pysely.query_compiler import CompiledQuery
from pysely.query_executor import QueryExecutor
from pysely.schema import Schema, table_node

DatabaseT = TypeVar("DatabaseT")
ScopeT = TypeVar("ScopeT")
ColumnsT = TypeVar("ColumnsT", bound=str)
RowT = TypeVar("RowT")
SchemaComparisonOperator: TypeAlias = Literal[
    "=", "!=", "<>", "<", "<=", ">", ">=", "is", "is not", "like", "not like"
]


@dataclass(frozen=True)
class SchemaQueryBuilder(Generic[DatabaseT, ScopeT, RowT]):
    _node: SelectQueryNode
    _executor: QueryExecutor
    _schema: Schema
    _scope: dict[str, str]
    _query_id: str

    @classmethod
    def from_name(cls, name: str, executor: QueryExecutor, schema: Schema) -> Self:
        return cls(
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

    def select_as(
        self, source: str, alias: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        node = self._schema.aliased_selection(self._scope, source, alias)
        return replace(
            self, _node=replace(self._node, selections=(*self._node.selections, node))
        )

    def where(
        self, column: str, operator: SchemaComparisonOperator, value: object
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        predicate = self._schema.predicate(self._scope, column, operator, value)
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


@dataclass(frozen=True)
class TypedSchemaQueryBuilder(Generic[DatabaseT, ColumnsT, RowT]):
    _query: SchemaQueryBuilder[DatabaseT, object, RowT]

    def select(
        self, selections: ColumnsT | list[ColumnsT] | tuple[ColumnsT, ...]
    ) -> Self:
        values = cast(str | list[str] | tuple[str, ...], selections)
        return replace(self, _query=self._query.select(values))

    def _select_as(self, source: ColumnsT, alias: str) -> Self:
        return replace(self, _query=self._query.select_as(source, alias))

    def where(
        self, column: ColumnsT, operator: SchemaComparisonOperator, value: object
    ) -> Self:
        return replace(self, _query=self._query.where(column, operator, value))

    def _inner_join(self, table: str, left: str, right: str) -> Self:
        return replace(self, _query=self._query.inner_join(table, left, right))

    def compile(self) -> CompiledQuery[RowT]:
        return self._query.compile()

    async def execute(self) -> list[RowT]:
        return await self._query.execute()

    async def execute_take_first(self) -> RowT | None:
        return await self._query.execute_take_first()

    async def execute_take_first_or_throw(self) -> RowT:
        return await self._query.execute_take_first_or_throw()
