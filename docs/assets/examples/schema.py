from datetime import date, datetime
from decimal import Decimal
from typing import Literal


class PersonTable:
    id: int
    first_name: str
    last_name: str | None
    status: Literal["active", "inactive"]
    verified: bool
    created_at: datetime


class PetTable:
    id: int
    owner_id: int
    name: str
    species: Literal["cat", "dog", "hamster"]
    birth_date: date | None
    weight_kg: Decimal | None


class DatabaseSchema:
    person: PersonTable
    pet: PetTable
