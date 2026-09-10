from schema import Database

from pysely import Pysely

# The playground supplies the selected dialect.
db = Pysely(schema=Database, dialect=dialect)
species = "dog"

query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .where("first_name", "=", "Jennifer")
    .where("species", "=", species)
    .select(["first_name", "pet.name as pet_name"])
)

compiled = query.compile()
