from typing import Literal, assert_type

from test.fixtures.dialects import postgres_dialect
from test.fixtures.portable_schema import Database, DatabaseQuery, PersonColumns

db = Database(dialect=postgres_dialect())
person = db.select_from("person")
assert_type(person, DatabaseQuery[PersonColumns])

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
        ]
    ],
)
joined.where("species", "=", "dog")
joined.select(["first_name", "pet.name"])
