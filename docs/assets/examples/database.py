from __future__ import annotations

from typing import (
    Any,
    Literal,
    LiteralString,
    Never,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

from schema import DatabaseSchema

from pysely import Pysely, TypedSchemaQueryBuilder
from pysely.dialect import Dialect

PersonColumns: TypeAlias = Literal["person.id", "person.first_name", "first_name"]
PetColumns: TypeAlias = Literal[
    "pet.id",
    "pet.owner_id",
    "pet.name",
    "pet.species",
    "owner_id",
    "name",
    "species",
]
TableName: TypeAlias = Literal["person", "pet"]
AllColumns: TypeAlias = PersonColumns | PetColumns
ColumnT = TypeVar("ColumnT", bound=str)
ResultKeyT = TypeVar("ResultKeyT", bound=str)
ResultValueT = TypeVar("ResultValueT")
AliasT = TypeVar("AliasT", bound=LiteralString | Literal[""])


class DatabaseQuery(
    TypedSchemaQueryBuilder[DatabaseSchema, ColumnT, dict[ResultKeyT, ResultValueT]]
):
    @overload
    def select(
        self: DatabaseQuery[ColumnT | PersonColumns, ResultKeyT, ResultValueT],
        selections: Literal["person.id"],
    ) -> DatabaseQuery[
        ColumnT | PersonColumns, ResultKeyT | Literal["id"], ResultValueT | int
    ]: ...

    @overload
    def select(
        self: DatabaseQuery[ColumnT | PetColumns, ResultKeyT, ResultValueT],
        selections: Literal["pet.id"],
    ) -> DatabaseQuery[
        ColumnT | PetColumns, ResultKeyT | Literal["id"], ResultValueT | int
    ]: ...

    @overload
    def select(
        self: DatabaseQuery[ColumnT | PersonColumns, ResultKeyT, ResultValueT],
        selections: Literal["person.first_name", "first_name"],
    ) -> DatabaseQuery[
        ColumnT | PersonColumns, ResultKeyT | Literal["first_name"], ResultValueT | str
    ]: ...

    @overload
    def select(
        self: DatabaseQuery[ColumnT | PetColumns, ResultKeyT, ResultValueT],
        selections: Literal["pet.owner_id", "owner_id"],
    ) -> DatabaseQuery[
        ColumnT | PetColumns, ResultKeyT | Literal["owner_id"], ResultValueT | int
    ]: ...

    @overload
    def select(
        self: DatabaseQuery[ColumnT | PetColumns, ResultKeyT, ResultValueT],
        selections: Literal["pet.name", "name"],
    ) -> DatabaseQuery[
        ColumnT | PetColumns, ResultKeyT | Literal["name"], ResultValueT | str
    ]: ...

    @overload
    def select(
        self: DatabaseQuery[ColumnT | PetColumns, ResultKeyT, ResultValueT],
        selections: Literal["pet.species", "species"],
    ) -> DatabaseQuery[
        ColumnT | PetColumns, ResultKeyT | Literal["species"], ResultValueT | str
    ]: ...

    @overload
    def select(
        self, selections: ColumnT | list[ColumnT] | tuple[ColumnT, ...]
    ) -> DatabaseQuery[ColumnT, str, object]: ...

    def select(
        self, selections: str | list[Any] | tuple[str, ...]
    ) -> DatabaseQuery[Any, Any, Any]:
        return cast(DatabaseQuery[Any, Any, Any], super().select(cast(Any, selections)))

    @overload
    def select_as(
        self,
        source: Literal["person.id", "pet.id", "pet.owner_id", "owner_id"],
        alias: AliasT,
    ) -> DatabaseQuery[ColumnT, ResultKeyT | AliasT, ResultValueT | int]: ...

    @overload
    def select_as(
        self,
        source: Literal[
            "person.first_name",
            "first_name",
            "pet.name",
            "name",
            "pet.species",
            "species",
        ],
        alias: AliasT,
    ) -> DatabaseQuery[ColumnT, ResultKeyT | AliasT, ResultValueT | str]: ...

    @overload
    def select_as(
        self, source: ColumnT, alias: str
    ) -> DatabaseQuery[ColumnT, str, object]: ...

    def select_as(self, source: str, alias: str) -> DatabaseQuery[Any, Any, Any]:
        return cast(
            DatabaseQuery[Any, Any, Any], self._select_as(cast(Any, source), alias)
        )

    @overload
    def inner_join(
        self,
        table: Literal["person"],
        left: ColumnT | PersonColumns,
        right: ColumnT | PersonColumns,
    ) -> DatabaseQuery[ColumnT | PersonColumns, ResultKeyT, ResultValueT]: ...

    @overload
    def inner_join(
        self,
        table: Literal["pet"],
        left: ColumnT | PetColumns,
        right: ColumnT | PetColumns,
    ) -> DatabaseQuery[ColumnT | PetColumns, ResultKeyT, ResultValueT]: ...

    @overload
    def inner_join(
        self,
        table: TableName,
        left: ColumnT | AllColumns,
        right: ColumnT | AllColumns,
    ) -> DatabaseQuery[Any, ResultKeyT, ResultValueT]: ...

    def inner_join(
        self, table: str, left: str, right: str
    ) -> DatabaseQuery[Any, Any, Any]:
        return cast(DatabaseQuery[Any, Any, Any], self._inner_join(table, left, right))


class Database:
    def __init__(self, *, dialect: Dialect) -> None:
        self._client = Pysely(schema=DatabaseSchema, dialect=dialect)

    @overload
    def select_from(
        self, table: Literal["person"]
    ) -> DatabaseQuery[PersonColumns, Never, Never]: ...

    @overload
    def select_from(
        self, table: Literal["pet"]
    ) -> DatabaseQuery[PetColumns, Never, Never]: ...

    @overload
    def select_from(self, table: TableName) -> DatabaseQuery[Any, Never, Never]: ...

    def select_from(self, table: str) -> DatabaseQuery[Any, Never, Never]:
        return cast(
            DatabaseQuery[Any, Never, Never],
            DatabaseQuery(self._client.select_from(table)),
        )
