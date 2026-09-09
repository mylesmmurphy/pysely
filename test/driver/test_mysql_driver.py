from __future__ import annotations

import pytest

from pysely import MysqlDialect, Pysely, PyselyError
from test.fixtures.generated import users


class FakeCursor:
    def __init__(self) -> None:
        self.description: tuple[tuple[object, ...], ...] | None = None
        self.rowcount = -1
        self.lastrowid: int | None = None
        self.rows: list[tuple[object, ...]] = []
        self.closed = False

    async def execute(self, sql: str, parameters: tuple[object, ...]) -> None:
        if sql.startswith("select"):
            self.description = (("id",), ("email",))
            self.rows = [(1, "ada@example.com")]
            self.rowcount = 1
        elif sql.startswith("insert"):
            self.rowcount = 1
            self.lastrowid = 4
        elif sql.startswith("update"):
            self.rowcount = 2

    async def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    async def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, *, autocommit: bool = True) -> None:
        self.cursors: list[FakeCursor] = []
        self.transactions: list[str] = []
        self.autocommit = autocommit

    def cursor(self) -> FakeCursor:
        cursor = FakeCursor()
        self.cursors.append(cursor)
        return cursor

    def get_autocommit(self) -> bool:
        return self.autocommit

    async def begin(self) -> None:
        self.transactions.append("begin")

    async def commit(self) -> None:
        self.transactions.append("commit")

    async def rollback(self) -> None:
        self.transactions.append("rollback")


class FakePool:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.acquired = 0
        self.released = 0
        self.closed = False
        self.waited_closed = False

    async def acquire(self) -> FakeConnection:
        self.acquired += 1
        return self.connection

    def release(self, connection: FakeConnection) -> None:
        assert connection is self.connection
        self.released += 1

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.waited_closed = True


async def test_mysql_pool_execution_and_metadata() -> None:
    pool = FakePool()

    async with Pysely[object](dialect=MysqlDialect(pool=pool)) as db:
        rows = await db.select_from(users).select(users.c.id, users.c.email).execute()
        inserted = (
            await db.insert_into(users).values({"email": "new@example.com"}).execute()
        )
        updated = await db.update_table(users).set({"nickname": "Ada"}).execute()

    assert rows == [{"id": 1, "email": "ada@example.com"}]
    assert inserted.affected_rows == 1
    assert inserted.insert_id == 4
    assert updated.affected_rows == 2
    assert pool.acquired == 3
    assert pool.released == 3
    assert not pool.closed


async def test_owned_mysql_pool_closes_and_waits() -> None:
    pool = FakePool()
    db = Pysely[object](dialect=MysqlDialect(pool=pool, owns_pool=True))

    await db.destroy()

    assert pool.closed
    assert pool.waited_closed


async def test_mysql_transaction_pins_connection() -> None:
    pool = FakePool()
    db = Pysely[object](dialect=MysqlDialect(pool=pool))

    async with db.transaction() as tx:
        await tx.select_from(users).select(users.c.id, users.c.email).execute()

    await db.destroy()

    assert pool.acquired == 1
    assert pool.released == 1
    assert pool.connection.transactions == ["begin", "commit"]


async def test_mysql_rejects_and_releases_non_autocommit_connection() -> None:
    pool = FakePool()
    pool.connection = FakeConnection(autocommit=False)
    db = Pysely[object](dialect=MysqlDialect(pool=pool))

    with pytest.raises(PyselyError, match="autocommit"):
        await db.select_from(users).select(users.c.id).execute()

    assert pool.released == 1
