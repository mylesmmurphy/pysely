from __future__ import annotations

import asyncio
from collections.abc import Mapping

import pytest

from pysely import PostgresDialect, Pysely
from test.fixtures.generated import users


class FakeConnection:
    def __init__(self) -> None:
        self.commands: list[tuple[str, tuple[object, ...]]] = []
        self.fail_on: str | None = None

    async def fetch(self, sql: str, *parameters: object) -> list[Mapping[str, object]]:
        self.commands.append((sql, parameters))
        return [{"id": 1, "email": "ada@example.com"}]

    async def execute(self, sql: str, *parameters: object) -> str:
        self.commands.append((sql, parameters))
        if sql == self.fail_on:
            raise RuntimeError(f"{sql} failed")
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


async def test_pool_executes_and_closes_with_client() -> None:
    pool = FakePool()

    async with Pysely[object](dialect=PostgresDialect(pool=pool)) as db:
        rows = await db.select_from(users).select(users.c.id, users.c.email).execute()
        inserted = (
            await db.insert_into(users).values({"email": "new@example.com"}).execute()
        )

    assert rows == [{"id": 1, "email": "ada@example.com"}]
    assert inserted.affected_rows == 1
    assert pool.acquired == 2
    assert pool.released == 2
    assert pool.closed


async def test_destroy_is_idempotent() -> None:
    pool = FakePool()
    db = Pysely[object](dialect=PostgresDialect(pool=pool))

    await db.destroy()
    await db.destroy()

    assert pool.closed


async def test_pool_factory_is_lazy_and_called_once() -> None:
    pool = FakePool()
    calls = 0

    async def create_pool() -> FakePool:
        nonlocal calls
        calls += 1
        return pool

    db = Pysely[object](dialect=PostgresDialect(pool=create_pool))
    assert calls == 0

    await db.select_from(users).select(users.c.id).execute()
    await db.select_from(users).select(users.c.id).execute()
    await db.destroy()

    assert calls == 1
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


async def test_connection_scope_pins_one_pool_connection() -> None:
    pool = FakePool()
    db = Pysely[object](dialect=PostgresDialect(pool=pool))

    async with db.connection() as connection_db:
        await connection_db.select_from(users).select(users.c.id).execute()
        await connection_db.update_table(users).set({"nickname": "Ada"}).execute()

    await db.destroy()

    assert pool.acquired == 1
    assert pool.released == 1


async def test_commit_failure_rolls_back_and_releases_connection() -> None:
    pool = FakePool()
    pool.connection.fail_on = "commit"
    db = Pysely[object](dialect=PostgresDialect(pool=pool))

    with pytest.raises(RuntimeError, match="commit failed"):
        async with db.transaction():
            pass

    assert [command[0] for command in pool.connection.commands] == [
        "begin",
        "commit",
        "rollback",
    ]
    assert pool.released == 1


async def test_cancellation_rolls_back_and_releases_connection() -> None:
    pool = FakePool()
    db = Pysely[object](dialect=PostgresDialect(pool=pool))

    with pytest.raises(asyncio.CancelledError):
        async with db.transaction():
            raise asyncio.CancelledError

    assert [command[0] for command in pool.connection.commands] == [
        "begin",
        "rollback",
    ]
    assert pool.released == 1
