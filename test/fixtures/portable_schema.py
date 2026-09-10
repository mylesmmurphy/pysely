from __future__ import annotations

from typing import Any, Literal, TypeAlias, TypeVar, overload

from pysely import Pysely, TypedSchemaQueryBuilder
from pysely.dialect import Dialect


class PersonTable:
    id: int
    first_name: str


class PetTable:
    id: int
    owner_id: int
    name: str
    species: str


class DatabaseSchema:
    person: PersonTable
    pet: PetTable


PersonColumns: TypeAlias = Literal["person.id", "person.first_name", "first_name"]
PetColumns: TypeAlias = Literal[
    "pet.id", "pet.owner_id", "pet.name", "pet.species", "owner_id", "name", "species"
]
TableName: TypeAlias = Literal["person", "pet"]
AllColumns: TypeAlias = PersonColumns | PetColumns
ColumnT = TypeVar("ColumnT", bound=str)


class DatabaseQuery(
    TypedSchemaQueryBuilder[DatabaseSchema, ColumnT, dict[str, object]]
):
    @overload
    def inner_join(
        self,
        table: Literal["person"],
        left: ColumnT | PersonColumns,
        right: ColumnT | PersonColumns,
    ) -> DatabaseQuery[ColumnT | PersonColumns]: ...

    @overload
    def inner_join(
        self,
        table: Literal["pet"],
        left: ColumnT | PetColumns,
        right: ColumnT | PetColumns,
    ) -> DatabaseQuery[ColumnT | PetColumns]: ...

    @overload
    def inner_join(
        self,
        table: TableName,
        left: ColumnT | AllColumns,
        right: ColumnT | AllColumns,
    ) -> DatabaseQuery[Any]: ...

    def inner_join(self, table: str, left: str, right: str) -> DatabaseQuery[Any]:
        return self._inner_join(table, left, right)


class Database:
    def __init__(self, *, dialect: Dialect) -> None:
        self._client = Pysely(schema=DatabaseSchema, dialect=dialect)

    @overload
    def select_from(self, table: Literal["person"]) -> DatabaseQuery[PersonColumns]: ...

    @overload
    def select_from(self, table: Literal["pet"]) -> DatabaseQuery[PetColumns]: ...

    @overload
    def select_from(self, table: TableName) -> DatabaseQuery[Any]: ...

    def select_from(self, table: str) -> DatabaseQuery[Any]:
        return DatabaseQuery(self._client.select_from(table))
