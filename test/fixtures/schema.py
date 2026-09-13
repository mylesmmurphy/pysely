from datetime import date
from typing import Literal

from pysely import SchemaDefinition


class PersonTable:
    id: int
    first_name: str
    last_name: str | None
    status: Literal["active", "inactive"]


class PetTable:
    id: int
    owner_id: int
    name: str
    species: Literal["cat", "dog", "hamster"]
    born: date | None


class ToyTable:
    id: int
    pet_id: int
    name: str
    price: float


class DatabaseSchema(SchemaDefinition):
    person: PersonTable
    pet: PetTable
    toy: ToyTable
