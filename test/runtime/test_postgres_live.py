from __future__ import annotations

import importlib

import pytest

from pysely import PostgresDialect, Pysely, Table
from test.conftest import require_service
from test.fixtures.generated import (
    UserInsert,
    UserRow,
    UsersColumns,
    UserUpdate,
)

users = Table[UserRow, UserInsert, UserUpdate, UsersColumns](
    name="users",
    columns=UsersColumns("users"),
    columns_factory=UsersColumns,
)


async def test_postgres_live_read_write_and_rollback(
    pytestconfig: pytest.Config,
) -> None:
    dsn = require_service(pytestconfig, "postgres", "PYSELY_POSTGRES_DSN")
    asyncpg = importlib.import_module("asyncpg")
    pool = await asyncpg.create_pool(dsn)
    async with pool.acquire() as connection:
        await connection.execute("drop table if exists users")
        await connection.execute(
            "create table users ("
            "id integer generated always as identity primary key, "
            "email text not null, nickname text)"
        )

    db = Pysely[object](dialect=PostgresDialect(pool=pool, owns_pool=True))
    inserted = await (
        db.insert_into(users)
        .values({"email": "ada@example.com"})
        .returning(users.c.id, users.c.email)
        .execute_take_first_or_throw()
    )

    with pytest.raises(RuntimeError, match="rollback"):
        async with db.transaction() as tx:
            await (
                tx.insert_into(users)
                .values({"email": "rollback@example.com"})
                .execute()
            )
            raise RuntimeError("rollback")

    rows = await db.select_from(users).select(users.c.id, users.c.email).execute()
    await db.destroy()

    assert inserted == {"id": 1, "email": "ada@example.com"}
    assert rows == [inserted]
