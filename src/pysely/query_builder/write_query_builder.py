from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Generic, TypeVar, cast, overload
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
from pysely.schema import Schema, table_node

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
    _schema: Schema | None = None
    _scope: dict[str, str] | None = None
    _table_name: str | None = None

    def values(
        self, values: InputT | Mapping[str, object]
    ) -> InsertQueryBuilder[InputT, ResultT]:
        row = _mapping(values)
        if self._schema is not None and self._table_name is not None:
            self._schema.validate_values(self._table_name, row)
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
        self,
        *expressions: OperationExpression | str | list[str] | tuple[str, ...],
    ) -> InsertQueryBuilder[InputT, list[dict[str, object]]]:
        node = replace(
            self._node,
            returning=(
                *self._node.returning,
                *_returning_nodes(expressions, self._schema, self._scope),
            ),
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
    _schema: Schema | None = None
    _scope: dict[str, str] | None = None
    _table_name: str | None = None

    def set(
        self, values: InputT | Mapping[str, object]
    ) -> UpdateQueryBuilder[InputT, ResultT]:
        row = _mapping(values)
        if self._schema is not None and self._table_name is not None:
            self._schema.validate_values(self._table_name, row)
        assignments = tuple(
            (IdentifierNode(name), ValueNode(value)) for name, value in row.items()
        )
        return replace(
            self,
            _node=replace(
                self._node,
                assignments=(*self._node.assignments, *assignments),
            ),
        )

    @overload
    def where(
        self, expression: Expression[bool]
    ) -> UpdateQueryBuilder[InputT, ResultT]: ...

    @overload
    def where(
        self, expression: str, operator: str, value: object
    ) -> UpdateQueryBuilder[InputT, ResultT]: ...

    def where(
        self,
        expression: Expression[bool] | str,
        operator: str | None = None,
        value: object = None,
    ) -> UpdateQueryBuilder[InputT, ResultT]:
        predicate = _predicate(expression, operator, value, self._schema, self._scope)
        return replace(
            self, _node=replace(self._node, where=_where(self._node.where, predicate))
        )

    def where_ref(
        self,
        left: OperationExpression,
        operator: ComparisonOperator,
        right: OperationExpression,
    ) -> UpdateQueryBuilder[InputT, ResultT]:
        return self.where(compare_references(left, operator, right))

    def returning(
        self,
        *expressions: OperationExpression | str | list[str] | tuple[str, ...],
    ) -> UpdateQueryBuilder[InputT, list[dict[str, object]]]:
        node = replace(
            self._node,
            returning=(
                *self._node.returning,
                *_returning_nodes(expressions, self._schema, self._scope),
            ),
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
    _schema: Schema | None = None
    _scope: dict[str, str] | None = None

    @overload
    def where(self, expression: Expression[bool]) -> DeleteQueryBuilder[ResultT]: ...

    @overload
    def where(
        self, expression: str, operator: str, value: object
    ) -> DeleteQueryBuilder[ResultT]: ...

    def where(
        self,
        expression: Expression[bool] | str,
        operator: str | None = None,
        value: object = None,
    ) -> DeleteQueryBuilder[ResultT]:
        predicate = _predicate(expression, operator, value, self._schema, self._scope)
        return replace(
            self, _node=replace(self._node, where=_where(self._node.where, predicate))
        )

    def where_ref(
        self,
        left: OperationExpression,
        operator: ComparisonOperator,
        right: OperationExpression,
    ) -> DeleteQueryBuilder[ResultT]:
        return self.where(compare_references(left, operator, right))

    def returning(
        self,
        *expressions: OperationExpression | str | list[str] | tuple[str, ...],
    ) -> DeleteQueryBuilder[list[dict[str, object]]]:
        node = replace(
            self._node,
            returning=(
                *self._node.returning,
                *_returning_nodes(expressions, self._schema, self._scope),
            ),
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


def create_schema_insert_builder(
    table: str, executor: QueryExecutor, schema: Schema
) -> InsertQueryBuilder[Mapping[str, object], InsertResult]:
    scope = schema.add_table({}, table)
    name = next(iter(scope.values()))
    return InsertQueryBuilder(
        InsertQueryNode(table_node(table)),
        executor,
        uuid4().hex,
        schema,
        scope,
        name,
    )


def create_schema_update_builder(
    table: str, executor: QueryExecutor, schema: Schema
) -> UpdateQueryBuilder[Mapping[str, object], UpdateResult]:
    scope = schema.add_table({}, table)
    name = next(iter(scope.values()))
    return UpdateQueryBuilder(
        UpdateQueryNode(table_node(table)),
        executor,
        uuid4().hex,
        schema,
        scope,
        name,
    )


def create_schema_delete_builder(
    table: str, executor: QueryExecutor, schema: Schema
) -> DeleteQueryBuilder[DeleteResult]:
    scope = schema.add_table({}, table)
    return DeleteQueryBuilder(
        DeleteQueryNode(table_node(table)), executor, uuid4().hex, schema, scope
    )


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("write values must be a mapping")
    mapping = cast(Mapping[object, object], value)
    if not mapping:
        raise InvalidQueryError("write values cannot be empty")
    if not all(isinstance(key, str) for key in mapping):
        raise TypeError("write value keys must be strings")
    return cast(Mapping[str, object], mapping)


def _where(current: OperationNode | None, expression: OperationNode) -> OperationNode:
    return AndNode((current, expression)) if current else expression


def _predicate(
    expression: Expression[bool] | str,
    operator: str | None,
    value: object,
    schema: Schema | None,
    scope: dict[str, str] | None,
) -> OperationNode:
    if not isinstance(expression, str):
        return expression.node
    if schema is None or scope is None or operator is None:
        raise TypeError("string predicates require a schema-backed write builder")
    return schema.predicate(scope, expression, operator, value)


def _returning_nodes(
    expressions: tuple[OperationExpression | str | list[str] | tuple[str, ...], ...],
    schema: Schema | None,
    scope: dict[str, str] | None,
) -> tuple[OperationNode, ...]:
    nodes: list[OperationNode] = []
    for expression in expressions:
        items = expression if isinstance(expression, list | tuple) else (expression,)
        for item in items:
            if isinstance(item, str):
                if schema is None or scope is None:
                    raise TypeError(
                        "string returning fields require a schema-backed builder"
                    )
                nodes.append(schema.selection(scope, item))
            else:
                nodes.append(item.node)
    return tuple(nodes)
