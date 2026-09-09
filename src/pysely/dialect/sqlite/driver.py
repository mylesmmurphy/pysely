from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Protocol

from pysely.driver import DatabaseConnection, QueryResult
from pysely.errors import ClosedClientError, InvalidQueryError, PyselyError
from pysely.query_compiler import CompiledQuery


class _Cursor(Protocol):
    @property
    def description(self) -> tuple[tuple[object, ...], ...] | None: ...

    @property
    def rowcount(self) -> int: ...

    @property
    def lastrowid(self) -> int | None: ...

    def fetchall(self) -> Awaitable[Iterable[Iterable[object]]]: ...

    async def close(self) -> None: ...


class SqliteDatabaseLike(Protocol):
    @property
    def isolation_level(self) -> str | None: ...

    def execute(
        self, sql: str, parameters: tuple[object, ...] = ()
    ) -> Awaitable[_Cursor]: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def close(self) -> None: ...


SqliteDatabaseFactory = Callable[[], Awaitable[SqliteDatabaseLike]]
SqliteDatabaseProvider = SqliteDatabaseLike | SqliteDatabaseFactory


class SqliteConnection(DatabaseConnection):
    def __init__(self, connection: SqliteDatabaseLike) -> None:
        if connection.isolation_level is not None:
            raise PyselyError("SQLite databases passed to Pysely must use autocommit")
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
    def __init__(self, database: SqliteDatabaseProvider) -> None:
        self._database_factory = database if callable(database) else None
        self._database = None if callable(database) else database
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
            if self._database is None:
                if self._database_factory is None:
                    raise RuntimeError("SQLite driver has no database factory")
                self._database = await self._database_factory()
            self._connection = SqliteConnection(self._database)

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
            if self._database:
                await self._database.close()
            self._database = None
            self._connection = None
