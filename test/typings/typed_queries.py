"""Positive typing fixture: checked by pyright (strict) and mypy (strict).

Every claim here runs against ``test/fixtures/schema.py``, which CI regenerates
from ``test/fixtures/tables.py`` and diffs.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Never, TypeVar, assert_type

from pysely import Cons, Database, Nil
from test.fixtures.dialects import postgres_dialect
from test.fixtures.schema import (
    DatabaseClient,
    DatabaseQuery,
    PersonQuery,
    PersonScope,
    PetScope,
    schema,
)

db = Database(schema=schema, dialect=postgres_dialect())
assert_type(db, DatabaseClient)
person = db.select_from("person")
assert_type(person, PersonQuery[Nil])

# --- bare names: unique in the database, or the only table in scope
person.select("first_name")
person.select("id")
person.where("id", "=", 1)
person.where_ref("id", "=", "person.id")
person.select_as("id", "person_id")

joined = person.inner_join("pet", "owner_id", "person.id")
assert_type(
    joined.select("pet.id"),
    DatabaseQuery[
        Literal["person", "pet"],
        PersonScope | PetScope,
        Never,
        Cons[Literal["id"], int, Nil],
        Never,
    ],
)
three = joined.inner_join("toy", "toy.pet_id", "pet.id")
three.where_ref("toy.pet_id", "=", "pet.id").where("price", ">", 1.5)
three.select("toy.name").select("pet.name").select("first_name")


# --- per-key row values
async def rows() -> None:
    row = await (
        person.select("person.id")
        .select("first_name")
        .select("last_name")
        .select("status")
        .select_as("first_name", "given")
        .execute_take_first_or_throw()
    )
    assert_type(row["id"], int)
    assert_type(row["first_name"], str)
    assert_type(row["last_name"], str | None)
    assert_type(row["status"], Literal["active", "inactive"])
    assert_type(row["given"], str)
    assert_type(row.get("id"), int | None)
    assert_type(row.get("missing"), object)
    assert_type(row.to_dict(), dict[str, object])
    assert_type(dict(row.items()), dict[str, object])
    assert_type("id" in row, bool)
    assert_type(list(row), list[str])
    many = await person.select("first_name").execute()
    assert_type(many[0]["first_name"], str)
    maybe = await person.select("first_name").execute_take_first()
    if maybe is not None:
        assert_type(maybe["first_name"], str)


# --- outer joins
async def outer() -> None:
    left = await (
        person.left_join("pet", "owner_id", "person.id")
        .select("first_name")
        .select("pet.name")
        .select("born")
        .select_as("species", "kind")
        .execute_take_first_or_throw()
    )
    assert_type(left["first_name"], str)
    assert_type(left["name"], str | None)
    assert_type(left["born"], date | None)
    assert_type(left["kind"], Literal["cat", "dog", "hamster"] | None)

    # A selection made before a right join becomes nullable.
    right = await (
        person.select("first_name")
        .right_join("pet", "owner_id", "person.id")
        .select("pet.name")
        .execute_take_first_or_throw()
    )
    assert_type(right["first_name"], str | None)
    assert_type(right["name"], str | None)

    full = await (
        person.full_join("pet", "owner_id", "person.id")
        .select("person.id")
        .execute_take_first_or_throw()
    )
    assert_type(full["id"], int | None)

    # An inner join after a left join does not un-null the left-joined table.
    mixed = await (
        person.left_join("pet", "owner_id", "person.id")
        .inner_join("toy", "toy.pet_id", "pet.id")
        .select("pet.name")
        .select_as("toy.name", "toy_name")
        .execute_take_first_or_throw()
    )
    assert_type(mixed["name"], str | None)
    assert_type(mixed["toy_name"], str)


# --- list projections keep scope checks; every key of that row reads as object
async def lists(names: list[Literal["first_name", "last_name"]]) -> None:
    listed = await (
        person.select("person.id")
        .select(["first_name", "last_name"])
        .execute_take_first_or_throw()
    )
    assert_type(listed["id"], object)
    assert_type(listed["first_name"], object)
    assert_type(listed["anything"], object)
    person.select(("first_name", "status"))
    person.select(names)


# --- operator families
person.where("status", "=", "active")
person.where("status", "!=", "inactive")
person.where("first_name", "like", "J%")
person.where("first_name", "in", ["Ada", "Grace"])
person.where("person.id", "in", (1, 2))
person.where("last_name", "is", None)
person.where("first_name", "is not", None)
person.where("status", "in", ["active"])
joined.where("born", "<", date(2020, 1, 1))


# --- callbacks see the same scope and value types
joined.where(
    lambda eb: eb.and_(
        eb("status", "=", "active"),
        eb.or_(eb("species", "=", "cat"), eb("species", "in", ["dog"])),
        eb.not_(eb("last_name", "is", None)),
        eb.ref("owner_id", "=", "person.id"),
    )
)
person.where(lambda eb: eb("id", ">", 0))


# --- helpers: single-table queries carry their table class; joined queries
# name the tables they need
FieldsT = TypeVar("FieldsT")
NullT = TypeVar("NullT", bound=str)
StarT = TypeVar("StarT", bound=str)


def active_only(query: PersonQuery[FieldsT]) -> PersonQuery[FieldsT]:
    return query.where("status", "=", "active")


def dogs_only(
    query: DatabaseQuery[
        Literal["person", "pet"], PersonScope | PetScope, NullT, FieldsT, StarT
    ],
) -> DatabaseQuery[
    Literal["person", "pet"], PersonScope | PetScope, NullT, FieldsT, StarT
]:
    return query.where("species", "=", "dog")


active_only(person)
dogs_only(joined)
dogs_only(person.left_join("pet", "owner_id", "person.id"))


async def through_helper() -> None:
    row = await active_only(person.select("first_name")).execute_take_first_or_throw()
    assert_type(row["first_name"], str)


base = person.select("first_name")
branch_a = base.select("last_name")
branch_b = base.select("person.id")


async def branches() -> None:
    a = await branch_a.execute_take_first_or_throw()
    b = await branch_b.execute_take_first_or_throw()
    assert_type(a["last_name"], str | None)
    assert_type(b["id"], int)


# --- ordering, paging, grouping and set operations
person.select("first_name").order_by("last_name").order_by("id", "desc")
person.select("first_name").select_as("person.id", "pid").order_by("pid", "desc")
joined.select("pet.name").order_by("person.id").order_by("name")
person.select("id").limit(10).offset(20)
person.select("status").group_by("status").having(
    lambda eb: eb("status", "=", "active")
)
joined.select("species").group_by(["species", "person.id"]).having(
    lambda eb: eb("species", "in", ["cat", "dog"])
)
person.select("first_name").union(person.select_as("person.first_name", "first_name"))
person.select("first_name").union_all(
    db.select_from("pet").select_as("name", "first_name")
)


async def paged() -> None:
    row = await (
        person.select("first_name")
        .select_as("person.id", "pid")
        .order_by("pid")
        .limit(1)
        .execute_take_first_or_throw()
    )
    assert_type(row["pid"], int)
    united = await (
        person.select("first_name")
        .union(db.select_from("pet").select_as("name", "first_name"))
        .execute()
    )
    assert_type(united[0]["first_name"], str)
