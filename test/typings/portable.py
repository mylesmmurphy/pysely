from typing import Literal, assert_type

from pysely import Column, PostgresDialect, Pysely, Table
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

db = Pysely[object](dialect=PostgresDialect())
query = db.select_from(users).select(users.c.id, users.c.email)
assert_type(query.compile().parameters, tuple[object, ...])
