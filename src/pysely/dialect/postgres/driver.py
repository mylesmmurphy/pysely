from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Mapping
from importlib import import_module
from typing import Protocol, cast

from pysely.driver import DatabaseConnection, QueryResult
from pysely.errors import ClosedClientError, PyselyError
from pysely.operation_node import (
    SelectQueryNode,
)
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


class _AsyncpgModule(Protocol):
    def create_pool(self, dsn: str) -> Awaitable[PostgresPoolLike]: ...


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
    def __init__(
        self,
        *,
        pool: PostgresPoolLike | None = None,
        dsn: str | None = None,
        owns_pool: bool | None = None,
    ) -> None:
        if pool is None and dsn is None:
            raise ValueError("PostgreSQL requires a pool or DSN")
        if pool is not None and dsn is not None:
            raise ValueError("PostgreSQL accepts either a pool or DSN, not both")
        self._pool = pool
        self._dsn = dsn
        self._owns_pool = (pool is None) if owns_pool is None else owns_pool
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
            try:
                module = cast(_AsyncpgModule, import_module("asyncpg"))
            except ModuleNotFoundError as error:
                raise PyselyError(
                    "PostgreSQL execution requires the 'pysely[postgres]' extra"
                ) from error
            if self._dsn is None:
                raise RuntimeError("PostgreSQL driver has no DSN")
            self._pool = await module.create_pool(self._dsn)

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
            if self._pool and self._owns_pool:
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
