from __future__ import annotations

import importlib

import pytest

from pysely import MysqlDialect, Pysely, Table
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


async def test_mysql_live_read_write_and_rollback(pytestconfig: pytest.Config) -> None:
    host = require_service(pytestconfig, "mysql", "PYSELY_MYSQL_HOST")
    asyncmy = importlib.import_module("asyncmy")
    pool = await asyncmy.create_pool(
        host=host,
        user="root",
        password="pysely",
        db="pysely",
        autocommit=True,
    )
    connection = await pool.acquire()
    try:
        cursor = connection.cursor()
        try:
            await cursor.execute("drop table if exists users")
            await cursor.execute(
                "create table users ("
                "id integer auto_increment primary key, "
                "email text not null, nickname text)"
            )
        finally:
            await cursor.close()
    finally:
        pool.release(connection)

    db = Pysely[object](dialect=MysqlDialect(pool=pool, owns_pool=True))
    inserted = (
        await db.insert_into(users).values({"email": "ada@example.com"}).execute()
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

    assert inserted.insert_id == 1
    assert rows == [{"id": 1, "email": "ada@example.com"}]
