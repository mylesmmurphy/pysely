from pathlib import Path

import aiosqlite
import pytest

from pysely import (
    Database as make_database,
)
from pysely import (
    InvalidQueryError,
    MysqlDialect,
    PostgresDialect,
    Pysely,
    Row,
    SqliteDialect,
    UnsupportedFeatureError,
)
from pysely.operation_node import OperationNodeTransformer, OperationNodeVisitor
from test.fixtures.dialects import _unavailable_database
from test.fixtures.schema import DatabaseClient, DatabaseRow, schema


class PersonTable:
    id: int
    first_name: str


class PetTable:
    id: int
    owner_id: int
    name: str
    species: str


class Database:
    person: PersonTable
    pet: PetTable


def test_string_query_compilation_and_scope() -> None:
    db = Pysely(schema=Database, dialect=PostgresDialect(pool=_unavailable_database))
    base = db.select_from("person")
    query = (
        base.inner_join("pet", "owner_id", "person.id")
        .where("first_name", "=", "Jennifer")
        .where("species", "=", "dog")
        .select("first_name")
        .select_as("pet.name", "pet_name")
    )
    compiled = query.compile()
    assert compiled.sql == (
        'select "first_name", "pet"."name" as "pet_name" from "person" '
        'inner join "pet" on "owner_id" = "person"."id" '
        'where ("first_name" = $1 and "species" = $2)'
    )
    assert compiled.parameters == ("Jennifer", "dog")
    assert OperationNodeTransformer().transform(compiled.query) == compiled.query
    OperationNodeVisitor().visit(compiled.query)
    with pytest.raises(InvalidQueryError, match="Unknown column"):
        base.select("pet.name")
    with pytest.raises(InvalidQueryError, match="Unknown column"):
        base.select_as("pet.name", "pet_name")
    with pytest.raises(InvalidQueryError, match="Ambiguous column"):
        query.select("id")
    with pytest.raises(InvalidQueryError, match="Unknown table"):
        db.select_from("missing")


def test_select_as_quotes_dynamic_and_duplicate_aliases() -> None:
    db = Pysely(schema=Database, dialect=PostgresDialect(pool=_unavailable_database))
    alias = 'display "name"'
    compiled = (
        db.select_from("person")
        .select_as("first_name", alias)
        .select_as("id", alias)
        .compile()
    )
    assert compiled.sql == (
        'select "first_name" as "display ""name""", '
        '"id" as "display ""name""" from "person"'
    )


def generated() -> DatabaseClient:
    return make_database(
        schema=schema, dialect=PostgresDialect(pool=_unavailable_database)
    )


def test_generated_query_wrapper_uses_runtime_builder() -> None:
    compiled = (
        generated()
        .select_from("person")
        .inner_join("pet", "person.id", "pet.owner_id")
        .where("species", "=", "dog")
        .select("first_name")
        .select_as("pet.name", "pet_name")
        .compile()
    )
    assert compiled.sql == (
        'select "first_name", "pet"."name" as "pet_name" from "person" '
        'inner join "pet" on "person"."id" = "pet"."owner_id" '
        'where "species" = $1'
    )
    assert compiled.parameters == ("dog",)


def test_generated_boolean_groups_and_reference_comparisons() -> None:
    compiled = (
        generated()
        .select_from("person")
        .inner_join("pet", "person.id", "pet.owner_id")
        .where(
            lambda eb: eb.and_(
                eb("person.id", "!=", 0),
                eb.or_(
                    eb("species", "=", "cat"),
                    eb("species", "in", ["dog", "hamster"]),
                ),
                eb.not_(eb("last_name", "is", None)),
                eb.ref("person.id", "=", "pet.owner_id"),
            )
        )
        .where_ref("person.id", "=", "pet.owner_id")
        .select("person.id")
        .compile()
    )
    assert compiled.sql == (
        'select "person"."id" from "person" '
        'inner join "pet" on "person"."id" = "pet"."owner_id" '
        'where (("person"."id" != $1 and ("species" = $2 or "species" in ($3, $4)) '
        'and not ("last_name" is null) and "person"."id" = "pet"."owner_id") '
        'and "person"."id" = "pet"."owner_id")'
    )
    assert compiled.parameters == (0, "cat", "dog", "hamster")
    assert OperationNodeTransformer().transform(compiled.query) == compiled.query
    OperationNodeVisitor().visit(compiled.query)


def test_operator_families_take_distinct_value_shapes() -> None:
    person = generated().select_from("person").select("person.id")
    assert (
        person.where("first_name", "like", "J%")
        .compile()
        .sql.endswith('where "first_name" like $1')
    )
    assert (
        person.where("last_name", "is not", None)
        .compile()
        .sql.endswith('where "last_name" is not null')
    )
    assert (
        person.where("person.id", "not in", (1, 2))
        .compile()
        .sql.endswith('where "person"."id" not in ($1, $2)')
    )
    with pytest.raises(InvalidQueryError, match="cannot compare against None"):
        person.where("last_name", "=", None)
    with pytest.raises(InvalidQueryError, match="compares against None only"):
        person.where("last_name", "is", "x")
    with pytest.raises(InvalidQueryError, match="requires a list or tuple"):
        person.where("first_name", "in", "abc")
    with pytest.raises(InvalidQueryError, match="at least one value"):
        person.where("first_name", "in", []).compile()
    with pytest.raises(InvalidQueryError, match="Unsupported comparison operator"):
        person.where("first_name", "===", "x")


def test_join_kinds_compile_and_respect_dialect_support() -> None:
    def joined(db: Pysely[object]) -> str:
        return (
            db.select_from("person")
            .full_join("pet", "pet.owner_id", "person.id")
            .select("first_name")
            .compile()
            .sql
        )

    postgres = Pysely(
        schema=schema, dialect=PostgresDialect(pool=_unavailable_database)
    )
    assert joined(postgres) == (
        'select "first_name" from "person" '
        'full join "pet" on "pet"."owner_id" = "person"."id"'
    )
    left = (
        postgres.select_from("person")
        .left_join("pet", "pet.owner_id", "person.id")
        .right_join("toy", "toy.pet_id", "pet.id")
        .select("first_name")
        .compile()
        .sql
    )
    assert 'left join "pet"' in left and 'right join "toy"' in left
    mysql = Pysely(schema=schema, dialect=MysqlDialect(pool=_unavailable_database))
    with pytest.raises(UnsupportedFeatureError, match="full joins"):
        joined(mysql)


def test_scope_errors_match_the_static_rules() -> None:
    db = generated()
    person = db.select_from("person")
    joined = person.inner_join("pet", "owner_id", "person.id")
    person.select("id")
    with pytest.raises(InvalidQueryError, match="Ambiguous column"):
        joined.select("id")
    with pytest.raises(InvalidQueryError, match="Unknown column"):
        person.select_as("pet.name", "pet_name")
    with pytest.raises(InvalidQueryError, match="Unknown column"):
        person.inner_join("pet", "toy.pet_id", "person.id")
    with pytest.raises(InvalidQueryError, match="Unknown column"):
        person.where(lambda eb: eb("species", "=", "dog"))


SQLITE_FIXTURE = (
    "create table person (id integer, first_name text, last_name text, status text);"
    "create table pet"
    " (id integer, owner_id integer, name text, species text, born text);"
    "create table toy (id integer, pet_id integer, name text, price real);"
    "insert into person values"
    " (1, 'Jennifer', null, 'active'), (2, 'Bob', 'B', 'inactive');"
    "insert into pet values"
    " (10, 1, 'Fido', 'dog', null), (11, 99, 'Stray', 'cat', null);"
    "insert into toy values (100, 10, 'ball', 1.5);"
)


async def test_typed_client_returns_generated_rows(tmp_path: Path) -> None:
    database = await aiosqlite.connect(tmp_path / "typed.db", isolation_level=None)
    await database.executescript(SQLITE_FIXTURE)
    async with make_database(
        schema=schema, dialect=SqliteDialect(database=database)
    ) as db:
        query = (
            db.select_from("person")
            .where("status", "=", "active")
            .select("person.id")
            .select("first_name")
            .select("last_name")
            .select_as("first_name", "given")
        )
        rows = await query.execute()
        first = await query.execute_take_first()
        only = await query.execute_take_first_or_throw()
    assert [type(row) for row in rows] == [DatabaseRow]
    assert isinstance(only, Row) and first == only
    row = rows[0]
    assert (
        row["id"] == 1
        and row["first_name"] == "Jennifer"
        and row["given"] == "Jennifer"
    )
    assert row["last_name"] is None
    assert row.get("missing") is None and row.get("id") == 1
    assert "id" in row and "missing" not in row
    assert list(row) == ["id", "first_name", "last_name", "given"]
    assert (
        dict(row.items())
        == row.to_dict()
        == {
            "id": 1,
            "first_name": "Jennifer",
            "last_name": None,
            "given": "Jennifer",
        }
    )
    assert row == {
        "id": 1,
        "first_name": "Jennifer",
        "last_name": None,
        "given": "Jennifer",
    }
    assert repr(row).startswith("DatabaseRow({")
    with pytest.raises(KeyError):
        row["missing"]
    with pytest.raises(TypeError):
        row["id"] = 2  # type: ignore[index]


async def test_outer_joins_return_null_for_unmatched_rows(tmp_path: Path) -> None:
    database = await aiosqlite.connect(tmp_path / "joins.db", isolation_level=None)
    await database.executescript(SQLITE_FIXTURE)
    async with make_database(
        schema=schema, dialect=SqliteDialect(database=database)
    ) as db:
        left = await (
            db.select_from("person")
            .left_join("pet", "owner_id", "person.id")
            .select("first_name")
            .select("pet.name")
            .select_as("species", "kind")
            .execute()
        )
        right = await (
            db.select_from("person")
            .select("first_name")
            .right_join("pet", "owner_id", "person.id")
            .select("pet.name")
            .execute()
        )
        full = await (
            db.select_from("person")
            .full_join("pet", "owner_id", "person.id")
            .select("first_name")
            .select("pet.name")
            .execute()
        )
        anti = await (
            db.select_from("person")
            .left_join("pet", "owner_id", "person.id")
            .where("pet.name", "is", None)
            .select("first_name")
            .execute()
        )
    assert [row.to_dict() for row in left] == [
        {"first_name": "Jennifer", "name": "Fido", "kind": "dog"},
        {"first_name": "Bob", "name": None, "kind": None},
    ]
    assert sorted((row.to_dict() for row in right), key=repr) == sorted(
        [
            {"first_name": "Jennifer", "name": "Fido"},
            {"first_name": None, "name": "Stray"},
        ],
        key=repr,
    )
    assert len(full) == 3
    assert {"first_name": None, "name": "Stray"} in [row.to_dict() for row in full]
    assert {"first_name": "Bob", "name": None} in [row.to_dict() for row in full]
    assert [row["first_name"] for row in anti] == ["Bob"]


async def test_string_query_in_transaction_and_connection_scope(tmp_path: Path) -> None:
    database = await aiosqlite.connect(tmp_path / "schema.db", isolation_level=None)
    await database.executescript(
        "create table person (id integer, first_name text);"
        "create table pet (id integer, owner_id integer, name text, species text);"
        "insert into person values (1, 'Jennifer');"
        "insert into pet values (2, 1, 'Fido', 'dog');"
    )
    async with Pysely(schema=Database, dialect=SqliteDialect(database=database)) as db:
        async with db.transaction() as tx:
            rows = await (
                tx.select_from("person as p")
                .inner_join("pet", "pet.owner_id", "p.id")
                .select("p.first_name")
                .select_as("pet.name", "pet_name")
                .execute()
            )
        async with db.connection() as connection:
            assert await connection.select_from("person").select("id").execute() == [
                {"id": 1}
            ]
    assert rows == [{"first_name": "Jennifer", "pet_name": "Fido"}]
