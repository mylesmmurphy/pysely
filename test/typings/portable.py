from collections.abc import Mapping
from typing import Literal, assert_type

from pysely import (
    Column,
    DeleteQueryBuilder,
    DeleteResult,
    InsertQueryBuilder,
    InsertResult,
    Pysely,
    Table,
    UpdateQueryBuilder,
    UpdateResult,
)
from test.fixtures.dialects import postgres_dialect
from test.fixtures.generated import (
    UserInsert,
    UserRow,
    UsersColumns,
    UserUpdate,
    users,
)

assert_type(users.c.email, Column[str, str, str, Literal["email"], str])
assert_type(
    users.as_("u"),
    Table[UserRow, UserInsert, UserUpdate, UsersColumns],
)

db = Pysely[object](dialect=postgres_dialect())
query = db.select_from(users).select(users.c.id, users.c.email)
assert_type(query.compile().parameters, tuple[object, ...])

insert = db.insert_into(users).values({"email": "ada@example.com"})
assert_type(insert, InsertQueryBuilder[UserInsert, InsertResult])
assert_type(
    insert.returning(users.c.id),
    InsertQueryBuilder[UserInsert, list[dict[str, object]]],
)

update = db.update_table(users).set({"nickname": "Ada"})
assert_type(update, UpdateQueryBuilder[UserUpdate, UpdateResult])

delete = db.delete_from(users).where(users.c.id.eq(1))
assert_type(delete, DeleteQueryBuilder[DeleteResult])


class Database:
    users: UserRow


schema_db = Pysely(schema=Database, dialect=postgres_dialect())
schema_insert = schema_db.insert_into("users").values({"email": "ada@example.com"})
assert_type(
    schema_insert,
    InsertQueryBuilder[Mapping[str, object], InsertResult],
)
assert_type(
    schema_insert.returning(["id", "email"]),
    InsertQueryBuilder[Mapping[str, object], list[dict[str, object]]],
)
assert_type(
    schema_db.update_table("users").set({"nickname": "Ada"}),
    UpdateQueryBuilder[Mapping[str, object], UpdateResult],
)
assert_type(
    schema_db.delete_from("users").where("id", "=", 1),
    DeleteQueryBuilder[DeleteResult],
)
