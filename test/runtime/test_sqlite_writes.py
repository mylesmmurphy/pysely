from __future__ import annotations

import pytest

from pysely import DeleteResult, InsertResult, Pysely, UpdateResult
from test.runtime.test_sqlite_execution import create_database, sqlite_dialect, users


class UserTable:
    id: int
    email: str
    nickname: str | None


class Database:
    users: UserTable


async def test_insert_update_delete_with_returning(tmp_path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)

    async with Pysely[object](dialect=sqlite_dialect(database)) as db:
        inserted = await (
            db.insert_into(users)
            .values({"email": "linus@example.com"})
            .returning(users.c.id, users.c.email)
            .execute_take_first_or_throw()
        )
        updated = await (
            db.update_table(users)
            .set({"nickname": "Linus"})
            .where(users.c.id.eq(inserted["id"]))
            .returning(users.c.nickname)
            .execute()
        )
        deleted = await (
            db.delete_from(users)
            .where(users.c.id.eq(inserted["id"]))
            .returning(users.c.email)
            .execute()
        )

    assert inserted == {"id": 3, "email": "linus@example.com"}
    assert updated == [{"nickname": "Linus"}]
    assert deleted == [{"email": "linus@example.com"}]


async def test_non_returning_write_metadata(tmp_path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)

    async with Pysely[object](dialect=sqlite_dialect(database)) as db:
        inserted = (
            await db.insert_into(users).values({"email": "linus@example.com"}).execute()
        )
        updated = await (
            db.update_table(users)
            .set({"nickname": "Linus"})
            .where(users.c.email.eq("linus@example.com"))
            .execute()
        )
        deleted = await (
            db.delete_from(users).where(users.c.email.eq("linus@example.com")).execute()
        )

    assert inserted == InsertResult(affected_rows=1, insert_id=3)
    assert updated == UpdateResult(affected_rows=1, changed_rows=None)
    assert deleted == DeleteResult(affected_rows=1)


async def test_schema_backed_string_writes(tmp_path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)

    async with Pysely(schema=Database, dialect=sqlite_dialect(database)) as db:
        inserted = await (
            db.insert_into("users")
            .values({"email": "linus@example.com"})
            .returning(["id", "email"])
            .execute_take_first_or_throw()
        )
        updated = await (
            db.update_table("users")
            .set({"nickname": "Linus"})
            .where("id", "=", inserted["id"])
            .returning("nickname")
            .execute()
        )
        deleted = await (
            db.delete_from("users")
            .where("id", "=", inserted["id"])
            .returning("email")
            .execute()
        )

    assert inserted == {"id": 3, "email": "linus@example.com"}
    assert updated == [{"nickname": "Linus"}]
    assert deleted == [{"email": "linus@example.com"}]


async def test_transaction_commits_and_rolls_back_writes(tmp_path) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)
    db = Pysely[object](dialect=sqlite_dialect(database))

    async with db.transaction() as tx:
        await tx.insert_into(users).values({"email": "commit@example.com"}).execute()

    with pytest.raises(RuntimeError, match="rollback"):
        async with db.transaction() as tx:
            await (
                tx.insert_into(users)
                .values({"email": "rollback@example.com"})
                .execute()
            )
            raise RuntimeError("rollback")

    rows = await db.select_from(users).select(users.c.email).execute()
    await db.destroy()

    assert {row["email"] for row in rows} == {
        "ada@example.com",
        "grace@example.com",
        "commit@example.com",
    }
