class PersonTable:
    id: int
    first_name: str


class PetTable:
    id: int
    owner_id: int
    name: str
    species: str


class Database:
    person: PersonTable
    pet: PetTable
