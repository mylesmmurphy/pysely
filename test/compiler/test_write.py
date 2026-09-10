import pytest

from pysely import (
    InvalidQueryError,
    MssqlDialect,
    Pysely,
    UnsupportedFeatureError,
)
from test.fixtures.dialects import mysql_dialect, postgres_dialect
from test.fixtures.generated import users


class UserTable:
    id: int
    email: str
    nickname: str | None


class Database:
    users: UserTable


def test_postgres_insert_returning():
    db = Pysely[object](dialect=postgres_dialect())

    compiled = (
        db.insert_into(users)
        .values({"email": "ada@example.com"})
        .returning(users.c.id)
        .compile()
    )

    assert compiled.sql == (
        'insert into "public"."users" ("email") values ($1) returning "id"'
    )
    assert compiled.parameters == ("ada@example.com",)


def test_mssql_insert_output():
    db = Pysely[object](dialect=MssqlDialect())

    compiled = (
        db.insert_into(users)
        .values({"email": "ada@example.com"})
        .returning(users.c.id)
        .compile()
    )

    assert compiled.sql == (
        "insert into [public].[users] ([email]) output [inserted].[id] values (?)"
    )


def test_mysql_rejects_returning_before_execution():
    db = Pysely[object](dialect=mysql_dialect())
    query = (
        db.insert_into(users).values({"email": "ada@example.com"}).returning(users.c.id)
    )

    with pytest.raises(UnsupportedFeatureError, match="does not support returning"):
        query.compile()


def test_update_and_delete_compile_with_ordered_parameters():
    db = Pysely[object](dialect=postgres_dialect())

    update = (
        db.update_table(users)
        .set({"nickname": "Ada"})
        .where(users.c.email.eq("ada@example.com"))
        .returning(users.c.id)
        .compile()
    )
    delete = (
        db.delete_from(users)
        .where(users.c.email.eq("old@example.com"))
        .returning(users.c.id)
        .compile()
    )

    assert update.sql == (
        'update "public"."users" set "nickname" = $1 '
        'where "public"."users"."email" = $2 returning "id"'
    )
    assert update.parameters == ("Ada", "ada@example.com")
    assert delete.sql == (
        'delete from "public"."users" '
        'where "public"."users"."email" = $1 returning "id"'
    )
    assert delete.parameters == ("old@example.com",)


def test_bulk_insert_reorders_values_to_the_first_row():
    db = Pysely[object](dialect=postgres_dialect())

    compiled = (
        db.insert_into(users)
        .values({"email": "ada@example.com", "nickname": "Ada"})
        .values({"nickname": "Grace", "email": "grace@example.com"})
        .compile()
    )

    assert compiled.sql.endswith("values ($1, $2), ($3, $4)")
    assert compiled.parameters == (
        "ada@example.com",
        "Ada",
        "grace@example.com",
        "Grace",
    )


def test_schema_backed_string_writes_compile():
    db = Pysely(schema=Database, dialect=postgres_dialect())

    insert = (
        db.insert_into("users")
        .values({"email": "ada@example.com"})
        .returning(["id", "email"])
        .compile()
    )
    update = (
        db.update_table("users")
        .set({"nickname": "Ada"})
        .where("email", "=", "ada@example.com")
        .returning("id")
        .compile()
    )
    delete = (
        db.delete_from("users")
        .where("email", "=", "old@example.com")
        .returning("id")
        .compile()
    )

    assert (
        insert.sql
        == 'insert into "users" ("email") values ($1) returning "id", "email"'
    )
    assert update.sql == (
        'update "users" set "nickname" = $1 where "email" = $2 returning "id"'
    )
    assert delete.sql == ('delete from "users" where "email" = $1 returning "id"')


def test_schema_backed_string_writes_validate_columns():
    db = Pysely(schema=Database, dialect=postgres_dialect())

    with pytest.raises(InvalidQueryError, match="Unknown column for users: missing"):
        db.insert_into("users").values({"missing": True})
    with pytest.raises(
        InvalidQueryError, match="Unknown column in query scope: missing"
    ):
        db.delete_from("users").where("missing", "=", True)
