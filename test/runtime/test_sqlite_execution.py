from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from pysely import (
    ClosedClientError,
    InvalidQueryError,
    NoResultError,
    Pysely,
    PyselyError,
    SqliteDialect,
    Table,
)
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


async def create_database(path: str) -> None:
    async with aiosqlite.connect(path) as connection:
        await connection.execute(
            "create table users (id integer primary key, email text, nickname text)"
        )
        await connection.executemany(
            "insert into users (email, nickname) values (?, ?)",
            [
                ("ada@example.com", None),
                ("grace@example.com", "Amazing Grace"),
            ],
        )
        await connection.commit()


def sqlite_dialect(path: str) -> SqliteDialect:
    async def connect() -> aiosqlite.Connection:
        return await aiosqlite.connect(path, isolation_level=None)

    return SqliteDialect(database=connect)


async def test_accepts_database_and_closes_it(tmp_path: Path) -> None:
    path = str(tmp_path / "pysely.db")
    await create_database(path)
    database = await aiosqlite.connect(path, isolation_level=None)
    db = Pysely[object](dialect=SqliteDialect(database=database))

    rows = await db.select_from(users).select(users.c.id).execute()
    await db.destroy()

    assert rows == [{"id": 1}, {"id": 2}]
    with pytest.raises(ValueError, match="no active connection"):
        await database.execute("select 1")


async def test_requires_autocommit_database(tmp_path: Path) -> None:
    path = str(tmp_path / "pysely.db")
    await create_database(path)
    database = await aiosqlite.connect(path)
    db = Pysely[object](dialect=SqliteDialect(database=database))

    with pytest.raises(PyselyError, match="autocommit"):
        await db.select_from(users).select(users.c.id).execute()

    await db.destroy()


async def test_execute_and_take_first(tmp_path: Path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)

    async with Pysely[object](dialect=sqlite_dialect(database)) as db:
        rows = await (
            db.select_from(users)
            .select(users.c.id, users.c.email.as_("login"))
            .where(users.c.email.eq("ada@example.com"))
            .execute()
        )

        assert rows == [{"id": 1, "login": "ada@example.com"}]


async def test_take_first_or_throw(tmp_path: Path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)

    async with Pysely[object](dialect=sqlite_dialect(database)) as db:
        query = db.select_from(users).select(users.c.id).where(users.c.id.eq(99))

        with pytest.raises(NoResultError):
            await query.execute_take_first_or_throw()


async def test_transaction_releases_connection_after_rollback(tmp_path: Path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)
    db = Pysely[object](dialect=sqlite_dialect(database))

    with pytest.raises(RuntimeError, match="rollback"):
        async with db.transaction() as tx:
            row = await tx.select_from(users).select(users.c.id).execute_take_first()
            assert row == {"id": 1}
            raise RuntimeError("rollback")

    rows = await db.select_from(users).select(users.c.id).execute()
    assert rows == [{"id": 1}, {"id": 2}]
    await db.destroy()


async def test_duplicate_projection_names_are_rejected(tmp_path: Path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)

    async with Pysely[object](dialect=sqlite_dialect(database)) as db:
        query = db.select_from(users).select(users.c.id, users.c.id)

        with pytest.raises(InvalidQueryError, match="duplicate column names"):
            await query.execute()


async def test_destroy_is_idempotent_and_closes_execution(tmp_path: Path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)
    db = Pysely[object](dialect=sqlite_dialect(database))
    query = db.select_from(users).select(users.c.id)

    await query.execute()
    await db.destroy()
    await db.destroy()

    with pytest.raises(ClosedClientError):
        await query.execute()
