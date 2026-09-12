from schema import schema

from playground import dialect
from pysely import Database

db = Database(schema=schema, dialect=dialect)

# Try it: misspell a column, change "dog" to "bird", or select "id".
query = (
    db.select_from("person")
    .left_join("pet", "owner_id", "person.id")
    .where("status", "=", "active")
    .where(lambda eb: eb.or_(eb("species", "=", "dog"), eb("species", "is", None)))
    .select("person.id")
    .select("first_name")
    .select_as("pet.name", "pet_name")
)

compiled = query.compile()


async def run_query() -> None:
    row = await query.execute_take_first_or_throw()
    row["id"]  # hover: int
    row["first_name"]  # hover: str
    row["pet_name"]  # hover: str | None (left join)
    # row["missing"] is an error: it was not selected.
