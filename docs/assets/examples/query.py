from database import Database

from playground import dialect

db = Database(dialect=dialect)
species = "dog"

query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .where("first_name", "=", "Jennifer")
    .where("species", "=", species)
    .select("first_name")
    .select_as("pet.name", "pet_name")
)

compiled = query.compile()


async def show_results() -> None:
    results = await query.execute()
    for result in results:
        pet_name: str = result["pet_name"]
        print(pet_name)
