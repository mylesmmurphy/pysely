from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Generic, TypeVar, cast
from uuid import uuid4

from pysely.catalog import Table
from pysely.errors import InvalidQueryError, NoResultError
from pysely.expression import (
    ComparisonOperator,
    Expression,
    OperationExpression,
    compare_references,
)
from pysely.operation_node import (
    AndNode,
    DeleteQueryNode,
    IdentifierNode,
    InsertQueryNode,
    OperationNode,
    UpdateQueryNode,
    ValueNode,
)
from pysely.query_compiler import CompiledQuery
from pysely.query_executor import QueryExecutor

InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")
TableRowT = TypeVar("TableRowT")
TableInsertT = TypeVar("TableInsertT")
TableUpdateT = TypeVar("TableUpdateT")
TableColumnsT = TypeVar("TableColumnsT")


@dataclass(frozen=True, slots=True)
class InsertResult:
    affected_rows: int | None
    insert_id: object | None


@dataclass(frozen=True, slots=True)
class UpdateResult:
    affected_rows: int | None
    changed_rows: int | None


@dataclass(frozen=True, slots=True)
class DeleteResult:
    affected_rows: int | None


@dataclass(frozen=True, slots=True)
class InsertQueryBuilder(Generic[InputT, ResultT]):
    _node: InsertQueryNode
    _executor: QueryExecutor
    _query_id: str

    def values(self, values: InputT) -> InsertQueryBuilder[InputT, ResultT]:
        row = _mapping(values)
        if self._node.columns:
            names = tuple(column.name for column in self._node.columns)
            if set(row) != set(names):
                raise InvalidQueryError(
                    "bulk insert rows must contain the same columns"
                )
        else:
            names = tuple(row)

        columns = tuple(IdentifierNode(name) for name in names)
        value_nodes = tuple(ValueNode(row[name]) for name in names)
        node = replace(
            self._node,
            columns=columns,
            values=(*self._node.values, value_nodes),
        )
        return replace(self, _node=node)

    def returning(
        self, *expressions: OperationExpression
    ) -> InsertQueryBuilder[InputT, list[dict[str, object]]]:
        node = replace(
            self._node,
            returning=(*self._node.returning, *(item.node for item in expressions)),
        )
        return cast(
            InsertQueryBuilder[InputT, list[dict[str, object]]],
            replace(self, _node=node),
        )

    def compile(self) -> CompiledQuery[ResultT]:
        return cast(
            CompiledQuery[ResultT],
            self._executor.compile_query(self._node, self._query_id),
        )

    async def execute(self) -> ResultT:
        result = await self._executor.execute_query(self._node, self._query_id)
        if self._node.returning:
            return cast(ResultT, list(result.rows))
        return cast(ResultT, InsertResult(result.affected_rows, result.insert_id))

    async def execute_take_first_or_throw(self) -> dict[str, object]:
        rows = await self._execute_returning()
        if not rows:
            raise NoResultError("Query returned no rows")
        return rows[0]

    async def _execute_returning(self) -> list[dict[str, object]]:
        if not self._node.returning:
            raise InvalidQueryError("returning() is required")
        result = await self._executor.execute_query(self._node, self._query_id)
        return list(result.rows)


@dataclass(frozen=True, slots=True)
class UpdateQueryBuilder(Generic[InputT, ResultT]):
    _node: UpdateQueryNode
    _executor: QueryExecutor
    _query_id: str

    def set(self, values: InputT) -> UpdateQueryBuilder[InputT, ResultT]:
        assignments = tuple(
            (IdentifierNode(name), ValueNode(value))
            for name, value in _mapping(values).items()
        )
        return replace(
            self,
            _node=replace(
                self._node,
                assignments=(*self._node.assignments, *assignments),
            ),
        )

    def where(
        self, expression: Expression[bool]
    ) -> UpdateQueryBuilder[InputT, ResultT]:
        return replace(
            self, _node=replace(self._node, where=_where(self._node.where, expression))
        )

    def where_ref(
        self,
        left: OperationExpression,
        operator: ComparisonOperator,
        right: OperationExpression,
    ) -> UpdateQueryBuilder[InputT, ResultT]:
        return self.where(compare_references(left, operator, right))

    def returning(
        self, *expressions: OperationExpression
    ) -> UpdateQueryBuilder[InputT, list[dict[str, object]]]:
        node = replace(
            self._node,
            returning=(*self._node.returning, *(item.node for item in expressions)),
        )
        return cast(
            UpdateQueryBuilder[InputT, list[dict[str, object]]],
            replace(self, _node=node),
        )

    def compile(self) -> CompiledQuery[ResultT]:
        return cast(
            CompiledQuery[ResultT],
            self._executor.compile_query(self._node, self._query_id),
        )

    async def execute(self) -> ResultT:
        result = await self._executor.execute_query(self._node, self._query_id)
        if self._node.returning:
            return cast(ResultT, list(result.rows))
        return cast(
            ResultT,
            UpdateResult(result.affected_rows, result.changed_rows),
        )


@dataclass(frozen=True, slots=True)
class DeleteQueryBuilder(Generic[ResultT]):
    _node: DeleteQueryNode
    _executor: QueryExecutor
    _query_id: str

    def where(self, expression: Expression[bool]) -> DeleteQueryBuilder[ResultT]:
        return replace(
            self, _node=replace(self._node, where=_where(self._node.where, expression))
        )

    def where_ref(
        self,
        left: OperationExpression,
        operator: ComparisonOperator,
        right: OperationExpression,
    ) -> DeleteQueryBuilder[ResultT]:
        return self.where(compare_references(left, operator, right))

    def returning(
        self, *expressions: OperationExpression
    ) -> DeleteQueryBuilder[list[dict[str, object]]]:
        node = replace(
            self._node,
            returning=(*self._node.returning, *(item.node for item in expressions)),
        )
        return cast(
            DeleteQueryBuilder[list[dict[str, object]]],
            replace(self, _node=node),
        )

    def compile(self) -> CompiledQuery[ResultT]:
        return cast(
            CompiledQuery[ResultT],
            self._executor.compile_query(self._node, self._query_id),
        )

    async def execute(self) -> ResultT:
        result = await self._executor.execute_query(self._node, self._query_id)
        if self._node.returning:
            return cast(ResultT, list(result.rows))
        return cast(ResultT, DeleteResult(result.affected_rows))


def create_insert_builder(
    table: Table[TableRowT, TableInsertT, TableUpdateT, TableColumnsT],
    executor: QueryExecutor,
) -> InsertQueryBuilder[TableInsertT, InsertResult]:
    builder: InsertQueryBuilder[TableInsertT, InsertResult] = InsertQueryBuilder(
        InsertQueryNode(table.to_operation_node()), executor, uuid4().hex
    )
    return builder


def create_update_builder(
    table: Table[TableRowT, TableInsertT, TableUpdateT, TableColumnsT],
    executor: QueryExecutor,
) -> UpdateQueryBuilder[TableUpdateT, UpdateResult]:
    builder: UpdateQueryBuilder[TableUpdateT, UpdateResult] = UpdateQueryBuilder(
        UpdateQueryNode(table.to_operation_node()), executor, uuid4().hex
    )
    return builder


def create_delete_builder(
    table: Table[TableRowT, TableInsertT, TableUpdateT, TableColumnsT],
    executor: QueryExecutor,
) -> DeleteQueryBuilder[DeleteResult]:
    builder: DeleteQueryBuilder[DeleteResult] = DeleteQueryBuilder(
        DeleteQueryNode(table.to_operation_node()), executor, uuid4().hex
    )
    return builder


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("write values must be a mapping")
    mapping = cast(Mapping[object, object], value)
    if not mapping:
        raise InvalidQueryError("write values cannot be empty")
    if not all(isinstance(key, str) for key in mapping):
        raise TypeError("write value keys must be strings")
    return cast(Mapping[str, object], mapping)


def _where(
    current: OperationNode | None, expression: Expression[bool]
) -> OperationNode:
    return AndNode((current, expression.node)) if current else expression.node
