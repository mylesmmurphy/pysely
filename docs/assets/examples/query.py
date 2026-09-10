from typing import Literal

from database import Database

from playground import dialect

db = Database(dialect=dialect)
species: Literal["cat", "dog", "hamster"] = "dog"

query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .where("first_name", "=", "Jennifer")
    .where("species", "=", species)
    .where("person.status", "!=", "inactive")
    .select("first_name")
    .select("status")
    .select_as("pet.name", "pet_name")
    .select_as("pet.birth_date", "pet_birth_date")
)

compiled = query.compile()


async def run_query() -> None:
    rows = await query.execute()
    # Result keys are typed and offer autocomplete.
    rows[0]["first_name"]
    rows[0]["status"]
    rows[0]["pet_name"]
    rows[0]["pet_birth_date"]
