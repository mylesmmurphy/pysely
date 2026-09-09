from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

from pysely.driver import DatabaseConnection, QueryResult
from pysely.errors import ClosedClientError
from pysely.operation_node import SelectQueryNode
from pysely.query_compiler import CompiledQuery


class PostgresConnectionLike(Protocol):
    async def fetch(
        self, sql: str, *parameters: object
    ) -> list[Mapping[str, object]]: ...

    async def execute(self, sql: str, *parameters: object) -> str: ...


class PostgresPoolLike(Protocol):
    def acquire(self) -> Awaitable[PostgresConnectionLike]: ...

    async def release(self, connection: PostgresConnectionLike) -> None: ...

    async def close(self) -> None: ...


PostgresPoolFactory = Callable[[], Awaitable[PostgresPoolLike]]
PostgresPoolProvider = PostgresPoolLike | PostgresPoolFactory


class PostgresConnection(DatabaseConnection):
    def __init__(self, connection: PostgresConnectionLike) -> None:
        self._connection = connection

    @property
    def raw_connection(self) -> PostgresConnectionLike:
        return self._connection

    async def execute_query(
        self, query: CompiledQuery[object]
    ) -> QueryResult[dict[str, object]]:
        if _returns_rows(query):
            records = await self._connection.fetch(query.sql, *query.parameters)
            return QueryResult(rows=tuple(dict(record) for record in records))

        status = await self._connection.execute(query.sql, *query.parameters)
        return QueryResult(affected_rows=_affected_rows(status))

    async def begin(self) -> None:
        await self._connection.execute("begin")

    async def commit(self) -> None:
        await self._connection.execute("commit")

    async def rollback(self) -> None:
        await self._connection.execute("rollback")


class PostgresDriver:
    def __init__(self, pool: PostgresPoolProvider) -> None:
        self._pool_factory = pool if callable(pool) else None
        self._pool = None if callable(pool) else pool
        self._init_lock = asyncio.Lock()
        self._destroyed = False

    @property
    def binding_profile_name(self) -> str:
        return "postgres-asyncpg"

    async def init(self) -> None:
        if self._destroyed:
            raise ClosedClientError("PostgreSQL driver has been destroyed")
        if self._pool:
            return
        async with self._init_lock:
            if self._pool:
                return
            if self._pool_factory is None:
                raise RuntimeError("PostgreSQL driver has no pool factory")
            self._pool = await self._pool_factory()

    async def acquire_connection(self) -> DatabaseConnection:
        await self.init()
        if self._pool is None:
            raise RuntimeError("PostgreSQL driver failed to initialize")
        return PostgresConnection(await self._pool.acquire())

    async def release_connection(self, connection: DatabaseConnection) -> None:
        if self._pool is None or not isinstance(connection, PostgresConnection):
            raise ValueError("Connection does not belong to this driver")
        await self._pool.release(connection.raw_connection)

    async def destroy(self) -> None:
        async with self._init_lock:
            if self._destroyed:
                return
            self._destroyed = True
            if self._pool:
                await self._pool.close()
            self._pool = None


def _returns_rows(query: CompiledQuery[object]) -> bool:
    node = query.query
    if isinstance(node, SelectQueryNode):
        return True
    return bool(node.returning)


def _affected_rows(status: str) -> int | None:
    tail = status.rsplit(" ", 1)[-1]
    return int(tail) if tail.isdigit() else None
