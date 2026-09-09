from __future__ import annotations

from collections.abc import Mapping

from pysely import PostgresDialect, Pysely
from test.fixtures.generated import users


class FakeConnection:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, sql: str, *parameters: object) -> list[Mapping[str, object]]:
        self.commands.append((sql, parameters))
        return [{"id": 1, "email": "ada@example.com"}]

    async def execute(self, sql: str, *parameters: object) -> str:
        self.commands.append((sql, parameters))
        if sql.startswith("insert"):
            return "INSERT 0 1"
        if sql.startswith("update"):
            return "UPDATE 2"
        if sql.startswith("delete"):
            return "DELETE 3"
        return sql.upper()


class FakePool:
    def __init__(self) -> None:
        self.connection = FakeConnection()
        self.acquired = 0
        self.released = 0
        self.closed = False

    async def acquire(self) -> FakeConnection:
        self.acquired += 1
        return self.connection

    async def release(self, connection: FakeConnection) -> None:
        assert connection is self.connection
        self.released += 1

    async def close(self) -> None:
        self.closed = True


async def test_borrowed_pool_executes_and_is_not_closed() -> None:
    pool = FakePool()

    async with Pysely[object](
        dialect=PostgresDialect(pool=pool, owns_pool=False)
    ) as db:
        rows = await db.select_from(users).select(users.c.id, users.c.email).execute()
        inserted = (
            await db.insert_into(users).values({"email": "new@example.com"}).execute()
        )

    assert rows == [{"id": 1, "email": "ada@example.com"}]
    assert inserted.affected_rows == 1
    assert pool.acquired == 2
    assert pool.released == 2
    assert not pool.closed


async def test_owned_pool_is_closed() -> None:
    pool = FakePool()
    db = Pysely[object](dialect=PostgresDialect(pool=pool, owns_pool=True))

    await db.destroy()
    await db.destroy()

    assert pool.closed


async def test_transaction_pins_one_pool_connection() -> None:
    pool = FakePool()
    db = Pysely[object](dialect=PostgresDialect(pool=pool))

    async with db.transaction() as tx:
        await tx.select_from(users).select(users.c.id).execute()
        await tx.update_table(users).set({"nickname": "Ada"}).execute()

    await db.destroy()

    assert pool.acquired == 1
    assert pool.released == 1
    assert pool.connection.commands[0] == ("begin", ())
    assert pool.connection.commands[-1] == ("commit", ())
