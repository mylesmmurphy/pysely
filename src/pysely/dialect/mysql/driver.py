from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from pysely.driver import DatabaseConnection, QueryResult
from pysely.errors import ClosedClientError, InvalidQueryError, PyselyError
from pysely.query_compiler import CompiledQuery


class MysqlCursorLike(Protocol):
    description: tuple[tuple[object, ...], ...] | None
    rowcount: int
    lastrowid: int | None

    async def execute(self, sql: str, parameters: tuple[object, ...]) -> object: ...

    async def fetchall(self) -> list[tuple[object, ...]]: ...

    async def close(self) -> None: ...


class MysqlConnectionLike(Protocol):
    def cursor(self) -> MysqlCursorLike: ...

    def get_autocommit(self) -> bool: ...

    async def begin(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class MysqlPoolLike(Protocol):
    def acquire(self) -> Awaitable[MysqlConnectionLike]: ...

    def release(self, connection: MysqlConnectionLike) -> None: ...

    def close(self) -> None: ...

    async def wait_closed(self) -> None: ...


MysqlPoolFactory = Callable[[], Awaitable[MysqlPoolLike]]
MysqlPoolProvider = MysqlPoolLike | MysqlPoolFactory


class MysqlConnection(DatabaseConnection):
    def __init__(self, connection: MysqlConnectionLike) -> None:
        if not connection.get_autocommit():
            raise PyselyError("MySQL pools passed to Pysely must enable autocommit")
        self._connection = connection

    @property
    def raw_connection(self) -> MysqlConnectionLike:
        return self._connection

    async def execute_query(
        self, query: CompiledQuery[object]
    ) -> QueryResult[dict[str, object]]:
        cursor = self._connection.cursor()
        try:
            await cursor.execute(query.sql, query.parameters)
            rows = await cursor.fetchall() if cursor.description else []
            names = tuple(str(column[0]) for column in cursor.description or ())
            if len(names) != len(set(names)):
                raise InvalidQueryError(
                    "Query returned duplicate column names; alias each projection"
                )
            mapped = tuple(dict(zip(names, row, strict=True)) for row in rows)
            affected_rows = cursor.rowcount if cursor.rowcount >= 0 else None
            insert_id = cursor.lastrowid if cursor.description is None else None
            return QueryResult(
                rows=mapped,
                affected_rows=affected_rows,
                insert_id=insert_id,
            )
        finally:
            await cursor.close()

    async def begin(self) -> None:
        await self._connection.begin()

    async def commit(self) -> None:
        await self._connection.commit()

    async def rollback(self) -> None:
        await self._connection.rollback()


class MysqlDriver:
    def __init__(self, pool: MysqlPoolProvider) -> None:
        self._pool_factory = pool if callable(pool) else None
        self._pool = None if callable(pool) else pool
        self._init_lock = asyncio.Lock()
        self._destroyed = False

    @property
    def binding_profile_name(self) -> str:
        return "mysql-asyncmy"

    async def init(self) -> None:
        if self._destroyed:
            raise ClosedClientError("MySQL driver has been destroyed")
        if self._pool:
            return
        async with self._init_lock:
            if self._pool:
                return
            if self._pool_factory is None:
                raise RuntimeError("MySQL driver has no pool factory")
            self._pool = await self._pool_factory()

    async def acquire_connection(self) -> DatabaseConnection:
        await self.init()
        if self._pool is None:
            raise RuntimeError("MySQL driver failed to initialize")
        connection = await self._pool.acquire()
        try:
            return MysqlConnection(connection)
        except BaseException:
            self._pool.release(connection)
            raise

    async def release_connection(self, connection: DatabaseConnection) -> None:
        if self._pool is None or not isinstance(connection, MysqlConnection):
            raise ValueError("Connection does not belong to this driver")
        self._pool.release(connection.raw_connection)

    async def destroy(self) -> None:
        async with self._init_lock:
            if self._destroyed:
                return
            self._destroyed = True
            if self._pool:
                self._pool.close()
                await self._pool.wait_closed()
            self._pool = None
