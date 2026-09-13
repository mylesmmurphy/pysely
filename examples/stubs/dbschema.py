from pysely import SchemaDefinition


class PersonTable:
    id: int
    name: str


class PetTable:
    id: int
    owner_id: int
    name: str


class DatabaseSchema(SchemaDefinition):
    person: PersonTable
    pet: PetTable
