from typing import Literal, Never, assert_type

from test.fixtures.dialects import postgres_dialect
from test.fixtures.portable_helpers import select_pet_name
from test.fixtures.portable_schema import Database, DatabaseQuery, PersonColumns

db = Database(dialect=postgres_dialect())
person = db.select_from("person")
assert_type(person, DatabaseQuery[PersonColumns, Never, Never])

person.where("first_name", "=", "Jennifer")
person.select(["person.id", "first_name"])

joined = person.inner_join("pet", "person.id", "pet.owner_id")
assert_type(
    joined,
    DatabaseQuery[
        Literal[
            "person.id",
            "person.first_name",
            "first_name",
            "pet.id",
            "pet.owner_id",
            "pet.name",
            "pet.species",
            "owner_id",
            "name",
            "species",
        ],
        Never,
        Never,
    ],
)
joined.where("species", "=", "dog")
joined.select(["first_name", "pet.name"])

named = joined.select_as("pet.name", "pet_name")
assert_type(
    named,
    DatabaseQuery[
        Literal[
            "person.id",
            "person.first_name",
            "first_name",
            "pet.id",
            "pet.owner_id",
            "pet.name",
            "pet.species",
            "owner_id",
            "name",
            "species",
        ],
        Literal["pet_name"],
        str,
    ],
)

duplicate = named.select_as("person.id", "pet_name")
assert_type(
    duplicate,
    DatabaseQuery[
        Literal[
            "person.id",
            "person.first_name",
            "first_name",
            "pet.id",
            "pet.owner_id",
            "pet.name",
            "pet.species",
            "owner_id",
            "name",
            "species",
        ],
        Literal["pet_name"],
        str | int,
    ],
)


def dynamic_projection(alias: str) -> None:
    joined.select_as("pet.name", alias)


from_helper = select_pet_name(joined)
assert_type(
    from_helper,
    DatabaseQuery[
        Literal[
            "person.id",
            "person.first_name",
            "first_name",
            "pet.id",
            "pet.owner_id",
            "pet.name",
            "pet.species",
            "owner_id",
            "name",
            "species",
        ],
        Literal["pet_name"],
        str,
    ],
)


async def projections() -> None:
    row = await named.select("person.id").execute_take_first_or_throw()
    assert_type(row, dict[Literal["pet_name"], str])
    assert_type(row["pet_name"], str)
