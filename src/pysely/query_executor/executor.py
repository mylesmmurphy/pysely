from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pysely.driver import DatabaseConnection, Driver, QueryResult
from pysely.errors import PyselyError
from pysely.operation_node import RootOperationNode
from pysely.query_compiler import CompiledQuery, QueryCompiler


class QueryPlugin(Protocol):
    def transform_query(
        self, query: RootOperationNode, query_id: str
    ) -> RootOperationNode: ...

    def transform_result(
        self, result: QueryResult[dict[str, object]], query_id: str
    ) -> QueryResult[dict[str, object]]: ...


@dataclass(frozen=True, slots=True)
class QueryExecutor:
    compiler: QueryCompiler
    driver: Driver | None = None
    plugins: tuple[QueryPlugin, ...] = ()
    connection: DatabaseConnection | None = None

    def compile_query(
        self, query: RootOperationNode, query_id: str
    ) -> CompiledQuery[dict[str, object]]:
        transformed = query
        for plugin in self.plugins:
            candidate = plugin.transform_query(transformed, query_id)
            if type(candidate) is not type(transformed):
                raise TypeError("Query plugins must preserve the root operation type")
            transformed = candidate
        return self.compiler.compile(transformed, query_id)

    async def execute_query(
        self, query: RootOperationNode, query_id: str
    ) -> QueryResult[dict[str, object]]:
        compiled = self.compile_query(query, query_id)
        driver = self.driver
        if driver is None:
            raise PyselyError("This dialect is configured for compilation only")
        if compiled.binding_profile != driver.binding_profile_name:
            raise PyselyError(
                "Compiled query binding profile does not match the configured driver"
            )

        if self.connection:
            result = await self.connection.execute_query(compiled)
        else:
            await driver.init()
            connection = await driver.acquire_connection()
            try:
                result = await connection.execute_query(compiled)
            finally:
                await driver.release_connection(connection)

        for plugin in self.plugins:
            result = plugin.transform_result(result, query_id)
        return result

    def with_connection(self, connection: DatabaseConnection) -> QueryExecutor:
        return QueryExecutor(self.compiler, self.driver, self.plugins, connection)

    async def destroy(self) -> None:
        if self.driver:
            await self.driver.destroy()
