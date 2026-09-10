from pathlib import Path

import aiosqlite
import pytest

from pysely import InvalidQueryError, PostgresDialect, Pysely, SqliteDialect
from pysely.operation_node import OperationNodeTransformer, OperationNodeVisitor
from test.fixtures.dialects import _unavailable_database
from test.fixtures.portable_schema import Database as GeneratedDatabase


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


def test_generated_query_wrapper_uses_runtime_builder() -> None:
    db = GeneratedDatabase(dialect=PostgresDialect(pool=_unavailable_database))
    compiled = (
        db.select_from("person")
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
