"""Shared runtime for handwritten schemas with generated adjacent stubs."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from typing import Any, Generic, Self, TypeVar, TypeVarTuple, cast

from pysely.dialect import Dialect
from pysely.errors import NoResultError
from pysely.expression import Expression
from pysely.flat_row import FlatRow
from pysely.operation_node import JoinKind
from pysely.pysely import Pysely
from pysely.query_builder import (
    DeleteQueryBuilder,
    DeleteResult,
    ExpressionBuilder,
    InsertQueryBuilder,
    InsertResult,
    OrderDirection,
    ReferenceOperator,
    SchemaComparisonOperator,
    SetOperator,
    UpdateQueryBuilder,
    UpdateResult,
)
from pysely.query_builder.schema_query_builder import SchemaQueryBuilder
from pysely.query_compiler import CompiledQuery
from pysely.query_executor import QueryPlugin

ColumnsT = TypeVar("ColumnsT", bound=str)
StarT = TypeVar("StarT", bound=str)
FieldsT = TypeVarTuple("FieldsT")


@dataclass(frozen=True)
class QueryCore(Generic[ColumnsT, StarT, *FieldsT]):
    """One runtime query implementation for every stub-generated query type."""

    _query: SchemaQueryBuilder[object, object, dict[str, object]]

    def select(self, selections: ColumnsT | Sequence[ColumnsT]) -> Self:
        return replace(self, _query=self._query.select(selections))

    def select_as(self, source: ColumnsT, alias: str) -> Self:
        return replace(self, _query=self._query.select_as(source, alias))

    def where_ref(
        self, left: ColumnsT, operator: ReferenceOperator, right: ColumnsT
    ) -> Self:
        return replace(self, _query=self._query.where_ref(left, operator, right))

    def _join(self, kind: JoinKind, table: str, left: str, right: str) -> Self:
        return replace(self, _query=self._query.join(kind, table, left, right))

    def inner_join(self, table: str, left: str, right: str) -> Self:
        return self._join("inner", table, left, right)

    def left_join(self, table: str, left: str, right: str) -> Self:
        return self._join("left", table, left, right)

    def right_join(self, table: str, left: str, right: str) -> Self:
        return self._join("right", table, left, right)

    def full_join(self, table: str, left: str, right: str) -> Self:
        return self._join("full", table, left, right)

    def group_by(self, columns: ColumnsT | Sequence[ColumnsT]) -> Self:
        return replace(self, _query=self._query.group_by(columns))

    def order_by(self, column: str, direction: OrderDirection = "asc") -> Self:
        return replace(self, _query=self._query.order_by(column, direction))

    def limit(self, count: int) -> Self:
        return replace(self, _query=self._query.limit(count))

    def offset(self, count: int) -> Self:
        return replace(self, _query=self._query.offset(count))

    def _set_operation(
        self, operator: SetOperator, other: QueryCore[Any, StarT, *FieldsT]
    ) -> Self:
        return replace(self, _query=self._query.set_operation(operator, other._query))

    def union(self, other: QueryCore[Any, StarT, *FieldsT]) -> Self:
        return self._set_operation("union", other)

    def union_all(self, other: QueryCore[Any, StarT, *FieldsT]) -> Self:
        return self._set_operation("union all", other)

    def intersect(self, other: QueryCore[Any, StarT, *FieldsT]) -> Self:
        return self._set_operation("intersect", other)

    def except_(self, other: QueryCore[Any, StarT, *FieldsT]) -> Self:
        return self._set_operation("except", other)

    def compile(self) -> CompiledQuery[FlatRow[StarT, *FieldsT]]:
        return cast(CompiledQuery[FlatRow[StarT, *FieldsT]], self._query.compile())

    async def execute(self) -> list[FlatRow[StarT, *FieldsT]]:
        return [FlatRow(row) for row in await self._query.execute()]

    async def execute_take_first(self) -> FlatRow[StarT, *FieldsT] | None:
        rows = await self.execute()
        return rows[0] if rows else None

    async def execute_take_first_or_throw(self) -> FlatRow[StarT, *FieldsT]:
        row = await self.execute_take_first()
        if row is None:
            raise NoResultError("Query returned no rows")
        return row


class FlatQuery(QueryCore[ColumnsT, StarT, *FieldsT]):
    def where(
        self,
        column: ColumnsT | Callable[[ExpressionBuilder[str]], Expression[bool]],
        operator: SchemaComparisonOperator | None = None,
        value: object = None,
    ) -> Self:
        if callable(column):
            return replace(self, _query=self._query.where(column))
        if operator is None:
            raise TypeError("where() requires an operator and value")
        return replace(self, _query=self._query.where(column, operator, value))

    def having(
        self, column: Callable[[ExpressionBuilder[str]], Expression[bool]]
    ) -> Self:
        return replace(self, _query=self._query.having(column))


class SchemaClient:
    """Connection owner; generated client classes only exist to type this API."""

    def __init__(
        self,
        *,
        schema: type[object],
        dialect: Dialect,
        plugins: tuple[QueryPlugin, ...] = (),
    ) -> None:
        self._db = Pysely[object](schema=schema, dialect=dialect, plugins=plugins)

    def select_from(self, table: str) -> FlatQuery[str, Any, *tuple[Any, ...]]:
        return FlatQuery(self._db.select_from(table))

    def insert_into(
        self, table: str
    ) -> InsertQueryBuilder[Mapping[str, object], InsertResult]:
        return self._db.insert_into(table)

    def update_table(
        self, table: str
    ) -> UpdateQueryBuilder[Mapping[str, object], UpdateResult]:
        return self._db.update_table(table)

    def delete_from(self, table: str) -> DeleteQueryBuilder[DeleteResult]:
        return self._db.delete_from(table)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.destroy()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[Self]:
        async with self._db.transaction() as database:
            client = type(self).__new__(type(self))
            client._db = database
            yield client

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[Self]:
        async with self._db.connection() as database:
            client = type(self).__new__(type(self))
            client._db = database
            yield client

    async def destroy(self) -> None:
        await self._db.destroy()


class SchemaDefinition:
    """Base for handwritten schemas. Codegen specializes connect() in a stub."""

    @classmethod
    def connect(
        cls,
        *,
        dialect: Dialect,
        plugins: tuple[QueryPlugin, ...] = (),
    ) -> SchemaClient:
        return SchemaClient(schema=cls, dialect=dialect, plugins=plugins)
