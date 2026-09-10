from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Generic, TypeVar, overload

from pysely.catalog import Table
from pysely.dialect import Dialect
from pysely.driver import DatabaseConnection
from pysely.query_builder import (
    DeleteQueryBuilder,
    DeleteResult,
    InsertQueryBuilder,
    InsertResult,
    SelectQueryBuilder,
    UpdateQueryBuilder,
    UpdateResult,
)
from pysely.query_builder.schema_query_builder import SchemaQueryBuilder
from pysely.query_builder.write_query_builder import (
    create_delete_builder,
    create_insert_builder,
    create_schema_delete_builder,
    create_schema_insert_builder,
    create_schema_update_builder,
    create_update_builder,
)
from pysely.query_executor import QueryExecutor, QueryPlugin
from pysely.schema import Schema

DatabaseT = TypeVar("DatabaseT")
RowT = TypeVar("RowT")
InsertT = TypeVar("InsertT")
UpdateT = TypeVar("UpdateT")
ColumnsT = TypeVar("ColumnsT")


class Pysely(Generic[DatabaseT]):
    def __init__(
        self,
        *,
        dialect: Dialect,
        schema: type[DatabaseT] | None = None,
        plugins: tuple[QueryPlugin, ...] = (),
    ) -> None:
        self._executor = QueryExecutor(
            dialect.create_query_compiler(), dialect.driver, plugins
        )
        self._schema = Schema.from_type(schema) if schema is not None else None

    async def __aenter__(self) -> Pysely[DatabaseT]:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.destroy()

    @classmethod
    def from_executor(
        cls, executor: QueryExecutor, schema: Schema | None = None
    ) -> Pysely[DatabaseT]:
        client: Pysely[DatabaseT] = cls.__new__(cls)
        client._executor = executor
        client._schema = schema
        return client

    @overload
    def select_from(
        self, table: str
    ) -> SchemaQueryBuilder[DatabaseT, object, dict[str, object]]: ...

    @overload
    def select_from(
        self, table: Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> SelectQueryBuilder[dict[str, object]]: ...

    def select_from(
        self, table: str | Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> (
        SchemaQueryBuilder[DatabaseT, object, dict[str, object]]
        | SelectQueryBuilder[dict[str, object]]
    ):
        if isinstance(table, str):
            if self._schema is None:
                raise ValueError("Pass schema=Database to use string table references")
            return SchemaQueryBuilder[DatabaseT, object, dict[str, object]].from_name(
                table, self._executor, self._schema
            )
        return SelectQueryBuilder.from_table(table, self._executor)

    @overload
    def insert_into(
        self, table: str
    ) -> InsertQueryBuilder[Mapping[str, object], InsertResult]: ...

    @overload
    def insert_into(
        self, table: Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> InsertQueryBuilder[InsertT, InsertResult]: ...

    def insert_into(
        self, table: str | Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> (
        InsertQueryBuilder[Mapping[str, object], InsertResult]
        | InsertQueryBuilder[InsertT, InsertResult]
    ):
        if isinstance(table, str):
            if self._schema is None:
                raise ValueError("Pass schema=Database to use string table references")
            return create_schema_insert_builder(table, self._executor, self._schema)
        return create_insert_builder(table, self._executor)

    @overload
    def update_table(
        self, table: str
    ) -> UpdateQueryBuilder[Mapping[str, object], UpdateResult]: ...

    @overload
    def update_table(
        self, table: Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> UpdateQueryBuilder[UpdateT, UpdateResult]: ...

    def update_table(
        self, table: str | Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> (
        UpdateQueryBuilder[Mapping[str, object], UpdateResult]
        | UpdateQueryBuilder[UpdateT, UpdateResult]
    ):
        if isinstance(table, str):
            if self._schema is None:
                raise ValueError("Pass schema=Database to use string table references")
            return create_schema_update_builder(table, self._executor, self._schema)
        return create_update_builder(table, self._executor)

    @overload
    def delete_from(self, table: str) -> DeleteQueryBuilder[DeleteResult]: ...

    @overload
    def delete_from(
        self, table: Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> DeleteQueryBuilder[DeleteResult]: ...

    def delete_from(
        self, table: str | Table[RowT, InsertT, UpdateT, ColumnsT]
    ) -> DeleteQueryBuilder[DeleteResult]:
        if isinstance(table, str):
            if self._schema is None:
                raise ValueError("Pass schema=Database to use string table references")
            return create_schema_delete_builder(table, self._executor, self._schema)
        return create_delete_builder(table, self._executor)

    def transaction(self) -> TransactionContext[DatabaseT]:
        return TransactionContext(self._executor, self._schema)

    def connection(self) -> ConnectionContext[DatabaseT]:
        return ConnectionContext(self._executor, self._schema)

    async def destroy(self) -> None:
        await self._executor.destroy()


class TransactionContext(Generic[DatabaseT]):
    def __init__(self, executor: QueryExecutor, schema: Schema | None = None) -> None:
        self._executor = executor
        self._schema = schema
        self._connection: DatabaseConnection | None = None

    async def __aenter__(self) -> Pysely[DatabaseT]:
        driver = self._executor.driver
        if driver is None:
            raise RuntimeError("Transactions require a configured driver")
        await driver.init()
        connection = await driver.acquire_connection()
        try:
            await connection.begin()
        except BaseException:
            await driver.release_connection(connection)
            raise
        self._connection = connection
        return Pysely[DatabaseT].from_executor(
            self._executor.with_connection(connection), self._schema
        )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        driver = self._executor.driver
        connection = self._connection
        if driver is None or connection is None:
            return
        try:
            if exc_type is None:
                try:
                    await connection.commit()
                except BaseException:
                    await connection.rollback()
                    raise
            else:
                await connection.rollback()
        finally:
            await driver.release_connection(connection)
            self._connection = None


class ConnectionContext(Generic[DatabaseT]):
    def __init__(self, executor: QueryExecutor, schema: Schema | None = None) -> None:
        self._executor = executor
        self._schema = schema
        self._connection: DatabaseConnection | None = None

    async def __aenter__(self) -> Pysely[DatabaseT]:
        driver = self._executor.driver
        if driver is None:
            raise RuntimeError("Connection scopes require a configured driver")
        await driver.init()
        self._connection = await driver.acquire_connection()
        return Pysely[DatabaseT].from_executor(
            self._executor.with_connection(self._connection), self._schema
        )

    async def __aexit__(self, *exc_info: object) -> None:
        driver = self._executor.driver
        connection = self._connection
        if driver is None or connection is None:
            return
        try:
            await driver.release_connection(connection)
        finally:
            self._connection = None
