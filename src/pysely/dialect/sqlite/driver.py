from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from importlib import import_module
from typing import Protocol, cast

from pysely.driver import DatabaseConnection, QueryResult
from pysely.errors import ClosedClientError, InvalidQueryError, PyselyError
from pysely.query_compiler import CompiledQuery


class _Cursor(Protocol):
    description: tuple[tuple[object, ...], ...] | None
    rowcount: int
    lastrowid: int | None

    async def fetchall(self) -> list[tuple[object, ...]]: ...

    async def close(self) -> None: ...


class _Connection(Protocol):
    async def execute(
        self, sql: str, parameters: tuple[object, ...] = ()
    ) -> _Cursor: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def close(self) -> None: ...


class _AioSqliteModule(Protocol):
    def connect(
        self, database: str, *, isolation_level: None
    ) -> Awaitable[_Connection]: ...


class SqliteConnection(DatabaseConnection):
    def __init__(self, connection: _Connection) -> None:
        self._connection = connection

    async def execute_query(
        self, query: CompiledQuery[object]
    ) -> QueryResult[dict[str, object]]:
        cursor = await self._connection.execute(query.sql, query.parameters)
        try:
            rows = await cursor.fetchall()
            names = tuple(str(column[0]) for column in cursor.description or ())
            if len(names) != len(set(names)):
                raise InvalidQueryError(
                    "Query returned duplicate column names; alias each projection"
                )
            mapped = tuple(dict(zip(names, row, strict=True)) for row in rows)
            affected_rows = cursor.rowcount if cursor.rowcount >= 0 else None
            return QueryResult(
                rows=mapped,
                affected_rows=affected_rows,
                insert_id=cursor.lastrowid if cursor.description is None else None,
            )
        finally:
            await cursor.close()

    async def begin(self) -> None:
        cursor = await self._connection.execute("begin")
        await cursor.close()

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()

    async def close(self) -> None:
        await self._connection.close()


class SqliteDriver:
    def __init__(self, database: str) -> None:
        self._database = database
        self._connection: SqliteConnection | None = None
        self._destroyed = False
        self._init_lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()

    @property
    def binding_profile_name(self) -> str:
        return "sqlite-aiosqlite"

    async def init(self) -> None:
        if self._destroyed:
            raise ClosedClientError("SQLite driver has been destroyed")
        if self._connection:
            return
        async with self._init_lock:
            if self._connection:
                return
            try:
                module = cast(_AioSqliteModule, import_module("aiosqlite"))
            except ModuleNotFoundError as error:
                raise PyselyError(
                    "SQLite execution requires the 'pysely[sqlite]' extra"
                ) from error
            connection = await module.connect(self._database, isolation_level=None)
            self._connection = SqliteConnection(connection)

    async def acquire_connection(self) -> DatabaseConnection:
        await self.init()
        await self._connection_lock.acquire()
        if self._connection is None:
            self._connection_lock.release()
            raise RuntimeError("SQLite driver failed to initialize")
        return self._connection

    async def release_connection(self, connection: DatabaseConnection) -> None:
        if connection is not self._connection:
            raise ValueError("Connection does not belong to this driver")
        self._connection_lock.release()

    async def destroy(self) -> None:
        async with self._init_lock, self._connection_lock:
            self._destroyed = True
            if self._connection is None:
                return
            await self._connection.close()
            self._connection = None
