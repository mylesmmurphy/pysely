from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Generic, TypeVar, cast
from uuid import uuid4

from pysely.catalog import Table
from pysely.errors import NoResultError
from pysely.expression import Expression, OperationExpression
from pysely.operation_node import (
    AndNode,
    IdentifierNode,
    SelectAllNode,
    SelectQueryNode,
)
from pysely.query_compiler import CompiledQuery
from pysely.query_executor import QueryExecutor

RowT = TypeVar("RowT")
TableRowT = TypeVar("TableRowT")
TableInsertT = TypeVar("TableInsertT")
TableUpdateT = TypeVar("TableUpdateT")
TableColumnsT = TypeVar("TableColumnsT")


@dataclass(frozen=True, slots=True)
class SelectQueryBuilder(Generic[RowT]):
    _node: SelectQueryNode
    _executor: QueryExecutor
    _query_id: str

    @classmethod
    def from_table(
        cls,
        table: Table[TableRowT, TableInsertT, TableUpdateT, TableColumnsT],
        executor: QueryExecutor,
    ) -> SelectQueryBuilder[dict[str, object]]:
        return cast(
            SelectQueryBuilder[dict[str, object]],
            cls(
                SelectQueryNode(from_=(table.to_operation_node(),)),
                executor,
                uuid4().hex,
            ),
        )

    def select(self, *expressions: OperationExpression) -> SelectQueryBuilder[RowT]:
        nodes = tuple(expression.node for expression in expressions)
        query = replace(
            self._node,
            selections=(*self._node.selections, *nodes),
        )
        return replace(self, _node=query)

    def select_all(
        self,
        table: (
            Table[TableRowT, TableInsertT, TableUpdateT, TableColumnsT] | None
        ) = None,
    ) -> SelectQueryBuilder[RowT]:
        source: tuple[IdentifierNode, ...] = ()
        if table:
            source = (IdentifierNode(table.alias or table.name),)
        selection = SelectAllNode(source)
        return replace(
            self,
            _node=replace(self._node, selections=(*self._node.selections, selection)),
        )

    def clear_select(self) -> SelectQueryBuilder[RowT]:
        return replace(self, _node=replace(self._node, selections=()))

    def where(self, expression: Expression[bool]) -> SelectQueryBuilder[RowT]:
        predicate = expression.node
        if self._node.where:
            predicate = AndNode((self._node.where, predicate))
        return replace(self, _node=replace(self._node, where=predicate))

    def compile(self) -> CompiledQuery[RowT]:
        compiled = self._executor.compile_query(self._node, self._query_id)
        return CompiledQuery(
            sql=compiled.sql,
            parameters=compiled.parameters,
            query=compiled.query,
            query_id=compiled.query_id,
            binding_profile=compiled.binding_profile,
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
