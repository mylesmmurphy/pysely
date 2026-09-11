from database import DatabaseSchema

from playground import dialect
from pysely import Pysely

db = Pysely.create(schema=DatabaseSchema, dialect=dialect)

# Try it: misspell a column, or change "dog" to "bird".
query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .where("species", "=", "dog")
    .where("status", "=", "active")
    .select("first_name")
    .select("last_name")
    .select_as("pet.name", "pet_name")
)

compiled = query.compile()


async def run_query() -> None:
    rows = await query.execute()
    rows[0]["pet_name"]  # hover: str
    rows[0]["last_name"]  # hover: str | None
