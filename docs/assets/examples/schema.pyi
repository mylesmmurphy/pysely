"""Generated from docs/assets/examples/schema.py; type-only. Do not edit."""

# ruff: noqa: E501, I001
# fmt: off
# mypy: disable-error-code="override, overload-overlap, overload-cannot-match"
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportOverlappingOverload=false
from __future__ import annotations
from collections.abc import Callable, Sequence
from typing import Generic, Literal, LiteralString, Never, TypeAlias, TypeVar, overload, Self, TypeVarTuple
from pysely import Dialect, Expression, ExpressionBuilder, OrderDirection, QueryPlugin, SchemaDefinition
from pysely.flat_row import Field
from pysely.schema_definition import QueryCore, SchemaClient

class PersonTable:
    id: int
    first_name: str
    last_name: str | None
    status: Literal['active', 'inactive']

class PetTable:
    id: int
    owner_id: int
    name: str
    species: Literal['cat', 'dog', 'hamster']
PersonColumns: TypeAlias = Literal['person.id', 'person.first_name', 'person.last_name', 'person.status', 'id', 'first_name', 'last_name', 'status']
PersonScope: TypeAlias = Literal['person.id', 'person.first_name', 'person.last_name', 'person.status', 'first_name', 'last_name', 'status']
PetColumns: TypeAlias = Literal['pet.id', 'pet.owner_id', 'pet.name', 'pet.species', 'id', 'owner_id', 'name', 'species']
PetScope: TypeAlias = Literal['pet.id', 'pet.owner_id', 'pet.name', 'pet.species', 'owner_id', 'name', 'species']
TableName: TypeAlias = Literal['person', 'pet']
TableT = TypeVar('TableT', bound=str)
TablesT = TypeVar('TablesT', bound=str)
ColumnsT = TypeVar('ColumnsT', bound=str)
ColumnT = TypeVar('ColumnT', bound=str)
ScopeT = TypeVar('ScopeT', bound=str)
NullT = TypeVar('NullT', bound=str)
FieldsT = TypeVarTuple('FieldsT')
StarT = TypeVar('StarT', bound=str)
AliasT = TypeVar('AliasT', bound=LiteralString | Literal[''])
RestT = TypeVarTuple('RestT')
K1 = TypeVar('K1', bound=str)
K2 = TypeVar('K2', bound=str)
K3 = TypeVar('K3', bound=str)
K4 = TypeVar('K4', bound=str)
K5 = TypeVar('K5', bound=str)
K6 = TypeVar('K6', bound=str)
K7 = TypeVar('K7', bound=str)
K8 = TypeVar('K8', bound=str)
V1 = TypeVar('V1')
V2 = TypeVar('V2')
V3 = TypeVar('V3')
V4 = TypeVar('V4')
V5 = TypeVar('V5')
V6 = TypeVar('V6')
V7 = TypeVar('V7')
V8 = TypeVar('V8')

class _QueryScope(Generic[TablesT, NullT]): ...
G0 = TypeVar('G0', bound=str)
G1 = TypeVar('G1', bound=str)
G2 = TypeVar('G2', bound=str)
G3 = TypeVar('G3', bound=str)
BuilderT = TypeVar('BuilderT')

class DatabaseExpressionBuilder(ExpressionBuilder[ColumnT], Generic[ColumnT, G0, G1, G2, G3]):

    @overload
    def __call__(self, column: G0, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: int) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G0, operator: Literal['in', 'not in'], value: list[int] | tuple[int, ...]) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G1, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: str) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G1, operator: Literal['in', 'not in'], value: list[str] | tuple[str, ...]) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G1, operator: Literal['like', 'not like'], value: str) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G2, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: Literal['active', 'inactive']) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G2, operator: Literal['in', 'not in'], value: list[Literal['active', 'inactive']] | tuple[Literal['active', 'inactive'], ...]) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G2, operator: Literal['like', 'not like'], value: str) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G3, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: Literal['cat', 'dog', 'hamster']) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G3, operator: Literal['in', 'not in'], value: list[Literal['cat', 'dog', 'hamster']] | tuple[Literal['cat', 'dog', 'hamster'], ...]) -> Expression[bool]: ...

    @overload
    def __call__(self, column: G3, operator: Literal['like', 'not like'], value: str) -> Expression[bool]: ...

    @overload
    def __call__(self, column: ColumnT, operator: Literal['is', 'is not'], value: None) -> Expression[bool]: ...

class _Predicates(Generic[BuilderT, ColumnT, G0, G1, G2, G3]):

    @overload
    def where(self, column: G0, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: int) -> Self: ...

    @overload
    def where(self, column: G0, operator: Literal['in', 'not in'], value: list[int] | tuple[int, ...]) -> Self: ...

    @overload
    def where(self, column: G1, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: str) -> Self: ...

    @overload
    def where(self, column: G1, operator: Literal['in', 'not in'], value: list[str] | tuple[str, ...]) -> Self: ...

    @overload
    def where(self, column: G1, operator: Literal['like', 'not like'], value: str) -> Self: ...

    @overload
    def where(self, column: G2, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: Literal['active', 'inactive']) -> Self: ...

    @overload
    def where(self, column: G2, operator: Literal['in', 'not in'], value: list[Literal['active', 'inactive']] | tuple[Literal['active', 'inactive'], ...]) -> Self: ...

    @overload
    def where(self, column: G2, operator: Literal['like', 'not like'], value: str) -> Self: ...

    @overload
    def where(self, column: G3, operator: Literal['=', '!=', '<>', '<', '<=', '>', '>='], value: Literal['cat', 'dog', 'hamster']) -> Self: ...

    @overload
    def where(self, column: G3, operator: Literal['in', 'not in'], value: list[Literal['cat', 'dog', 'hamster']] | tuple[Literal['cat', 'dog', 'hamster'], ...]) -> Self: ...

    @overload
    def where(self, column: G3, operator: Literal['like', 'not like'], value: str) -> Self: ...

    @overload
    def where(self, column: ColumnT, operator: Literal['is', 'is not'], value: None) -> Self: ...

    @overload
    def where(self, column: Callable[[BuilderT], Expression[bool]]) -> Self: ...

    def having(self, column: Callable[[BuilderT], Expression[bool]]) -> Self: ...

class DatabaseQuery(_Predicates[DatabaseExpressionBuilder[ColumnT, G0, G1, G2, G3], ColumnT, G0, G1, G2, G3], _QueryScope[TablesT, NullT], QueryCore[ColumnT, StarT, *FieldsT], Generic[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, *FieldsT]):

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], selections: Literal['person.id']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[Literal['id'], int | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT], selections: Literal['person.id']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['id'], int], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], selections: Literal['person.first_name', 'first_name']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[Literal['first_name'], str | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT], selections: Literal['person.first_name', 'first_name']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['first_name'], str], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], selections: Literal['person.last_name', 'last_name']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[Literal['last_name'], str | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT], selections: Literal['person.last_name', 'last_name']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['last_name'], str | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], selections: Literal['person.status', 'status']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[Literal['status'], Literal['active', 'inactive'] | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['person'], NullT], selections: Literal['person.status', 'status']) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['status'], Literal['active', 'inactive']], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT | Literal['pet']], selections: Literal['pet.id']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT | Literal['pet'], StarT, G0, G1, G2, G3, Field[Literal['id'], int | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT], selections: Literal['pet.id']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['id'], int], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT | Literal['pet']], selections: Literal['pet.owner_id', 'owner_id']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT | Literal['pet'], StarT, G0, G1, G2, G3, Field[Literal['owner_id'], int | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT], selections: Literal['pet.owner_id', 'owner_id']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['owner_id'], int], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT | Literal['pet']], selections: Literal['pet.name', 'name']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT | Literal['pet'], StarT, G0, G1, G2, G3, Field[Literal['name'], str | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT], selections: Literal['pet.name', 'name']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['name'], str], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT | Literal['pet']], selections: Literal['pet.species', 'species']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT | Literal['pet'], StarT, G0, G1, G2, G3, Field[Literal['species'], Literal['cat', 'dog', 'hamster'] | None], *FieldsT]: ...

    @overload
    def select(self: _QueryScope[TablesT | Literal['pet'], NullT], selections: Literal['pet.species', 'species']) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[Literal['species'], Literal['cat', 'dog', 'hamster']], *FieldsT]: ...

    @overload
    def select(self, selections: ColumnT | Sequence[ColumnT]) -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[str, object], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], source: Literal['person.id'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[AliasT, int | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT], source: Literal['person.id'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[AliasT, int], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], source: Literal['person.first_name', 'first_name'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[AliasT, str | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT], source: Literal['person.first_name', 'first_name'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[AliasT, str], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], source: Literal['person.last_name', 'last_name'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[AliasT, str | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT], source: Literal['person.last_name', 'last_name'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[AliasT, str | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT | Literal['person']], source: Literal['person.status', 'status'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT | Literal['person'], StarT, G0, G1, G2, G3, Field[AliasT, Literal['active', 'inactive'] | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['person'], NullT], source: Literal['person.status', 'status'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['person'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[AliasT, Literal['active', 'inactive']], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['pet'], NullT | Literal['pet']], source: Literal['pet.id', 'pet.owner_id', 'owner_id'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT | Literal['pet'], StarT, G0, G1, G2, G3, Field[AliasT, int | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['pet'], NullT], source: Literal['pet.id', 'pet.owner_id', 'owner_id'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[AliasT, int], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['pet'], NullT | Literal['pet']], source: Literal['pet.name', 'name'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT | Literal['pet'], StarT, G0, G1, G2, G3, Field[AliasT, str | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['pet'], NullT], source: Literal['pet.name', 'name'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[AliasT, str], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['pet'], NullT | Literal['pet']], source: Literal['pet.species', 'species'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT | Literal['pet'], StarT, G0, G1, G2, G3, Field[AliasT, Literal['cat', 'dog', 'hamster'] | None], *FieldsT]: ...

    @overload
    def select_as(self: _QueryScope[TablesT | Literal['pet'], NullT], source: Literal['pet.species', 'species'], alias: AliasT) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT, NullT, StarT, G0, G1, G2, G3, Field[AliasT, Literal['cat', 'dog', 'hamster']], *FieldsT]: ...

    @overload
    def select_as(self, source: ColumnT, alias: str) -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[str, object], *FieldsT]: ...

    @overload
    def order_by(self, column: ColumnT, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, *FieldsT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], *RestT], column: K1, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], *RestT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], *RestT], column: K2, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], *RestT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], *RestT], column: K3, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], *RestT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], *RestT], column: K4, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], *RestT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], *RestT], column: K5, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], *RestT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], *RestT], column: K6, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], *RestT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], *RestT], column: K7, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], *RestT]: ...

    @overload
    def order_by(self: DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], Field[K8, V8], *RestT], column: K8, direction: OrderDirection='asc') -> DatabaseQuery[TablesT, ColumnT, NullT, StarT, G0, G1, G2, G3, Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], Field[K8, V8], *RestT]: ...

    @overload
    def inner_join(self, table: Literal['person'], left: ColumnT | PersonScope, right: ColumnT | PersonScope) -> DatabaseQuery[TablesT | Literal['person'], ColumnT | PersonScope, NullT, StarT, G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def inner_join(self, table: Literal['pet'], left: ColumnT | PetScope, right: ColumnT | PetScope) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT | PetScope, NullT, StarT, G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

    @overload
    def left_join(self, table: Literal['person'], left: ColumnT | PersonScope, right: ColumnT | PersonScope) -> DatabaseQuery[TablesT | Literal['person'], ColumnT | PersonScope, NullT | Literal['person'], StarT, G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def left_join(self, table: Literal['pet'], left: ColumnT | PetScope, right: ColumnT | PetScope) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT | PetScope, NullT | Literal['pet'], StarT, G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

    @overload
    def right_join(self, table: Literal['person'], left: ColumnT | PersonScope, right: ColumnT | PersonScope) -> DatabaseQuery[TablesT | Literal['person'], ColumnT | PersonScope, NullT, Literal['*'], G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def right_join(self, table: Literal['pet'], left: ColumnT | PetScope, right: ColumnT | PetScope) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT | PetScope, NullT, Literal['*'], G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

    @overload
    def full_join(self, table: Literal['person'], left: ColumnT | PersonScope, right: ColumnT | PersonScope) -> DatabaseQuery[TablesT | Literal['person'], ColumnT | PersonScope, NullT | Literal['person'], Literal['*'], G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def full_join(self, table: Literal['pet'], left: ColumnT | PetScope, right: ColumnT | PetScope) -> DatabaseQuery[TablesT | Literal['pet'], ColumnT | PetScope, NullT | Literal['pet'], Literal['*'], G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

class SingleTableQuery(QueryCore[ColumnsT, Literal[''], *FieldsT], Generic[TableT, ColumnsT, ScopeT, G0, G1, G2, G3, *FieldsT]):

    @overload
    def inner_join(self, table: Literal['person'], left: ScopeT | PersonScope, right: ScopeT | PersonScope) -> DatabaseQuery[TableT | Literal['person'], ScopeT | PersonScope, Never, Literal[''], G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def inner_join(self, table: Literal['pet'], left: ScopeT | PetScope, right: ScopeT | PetScope) -> DatabaseQuery[TableT | Literal['pet'], ScopeT | PetScope, Never, Literal[''], G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

    @overload
    def left_join(self, table: Literal['person'], left: ScopeT | PersonScope, right: ScopeT | PersonScope) -> DatabaseQuery[TableT | Literal['person'], ScopeT | PersonScope, Literal['person'], Literal[''], G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def left_join(self, table: Literal['pet'], left: ScopeT | PetScope, right: ScopeT | PetScope) -> DatabaseQuery[TableT | Literal['pet'], ScopeT | PetScope, Literal['pet'], Literal[''], G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

    @overload
    def right_join(self, table: Literal['person'], left: ScopeT | PersonScope, right: ScopeT | PersonScope) -> DatabaseQuery[TableT | Literal['person'], ScopeT | PersonScope, Never, Literal['*'], G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def right_join(self, table: Literal['pet'], left: ScopeT | PetScope, right: ScopeT | PetScope) -> DatabaseQuery[TableT | Literal['pet'], ScopeT | PetScope, Never, Literal['*'], G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

    @overload
    def full_join(self, table: Literal['person'], left: ScopeT | PersonScope, right: ScopeT | PersonScope) -> DatabaseQuery[TableT | Literal['person'], ScopeT | PersonScope, Literal['person'], Literal['*'], G0 | Literal['person.id'], G1 | Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], G2 | Literal['person.status', 'status'], G3, *FieldsT]: ...

    @overload
    def full_join(self, table: Literal['pet'], left: ScopeT | PetScope, right: ScopeT | PetScope) -> DatabaseQuery[TableT | Literal['pet'], ScopeT | PetScope, Literal['pet'], Literal['*'], G0 | Literal['pet.id', 'pet.owner_id', 'owner_id'], G1 | Literal['pet.name', 'name'], G2, G3 | Literal['pet.species', 'species'], *FieldsT]: ...

class PersonQuery(_Predicates[DatabaseExpressionBuilder[PersonColumns, Literal['person.id', 'id'], Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], Literal['person.status', 'status'], Never], PersonColumns, Literal['person.id', 'id'], Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], Literal['person.status', 'status'], Never], SingleTableQuery[Literal['person'], PersonColumns, PersonScope, Literal['person.id'], Literal['person.first_name', 'first_name', 'person.last_name', 'last_name'], Literal['person.status', 'status'], Never, *FieldsT], Generic[*FieldsT,]):

    @overload
    def select(self, selections: Literal['person.id', 'id']) -> PersonQuery[Field[Literal['id'], int], *FieldsT]: ...

    @overload
    def select(self, selections: Literal['person.first_name', 'first_name']) -> PersonQuery[Field[Literal['first_name'], str], *FieldsT]: ...

    @overload
    def select(self, selections: Literal['person.last_name', 'last_name']) -> PersonQuery[Field[Literal['last_name'], str | None], *FieldsT]: ...

    @overload
    def select(self, selections: Literal['person.status', 'status']) -> PersonQuery[Field[Literal['status'], Literal['active', 'inactive']], *FieldsT]: ...

    @overload
    def select(self, selections: PersonColumns | Sequence[PersonColumns]) -> PersonQuery[Field[str, object], *FieldsT]: ...

    @overload
    def select_as(self, source: Literal['person.id', 'id'], alias: AliasT) -> PersonQuery[Field[AliasT, int], *FieldsT]: ...

    @overload
    def select_as(self, source: Literal['person.first_name', 'first_name'], alias: AliasT) -> PersonQuery[Field[AliasT, str], *FieldsT]: ...

    @overload
    def select_as(self, source: Literal['person.last_name', 'last_name'], alias: AliasT) -> PersonQuery[Field[AliasT, str | None], *FieldsT]: ...

    @overload
    def select_as(self, source: Literal['person.status', 'status'], alias: AliasT) -> PersonQuery[Field[AliasT, Literal['active', 'inactive']], *FieldsT]: ...

    @overload
    def select_as(self, source: PersonColumns, alias: str) -> PersonQuery[Field[str, object], *FieldsT]: ...

    @overload
    def order_by(self, column: PersonColumns, direction: OrderDirection='asc') -> PersonQuery[*FieldsT,]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], *RestT], column: K1, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], *RestT]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], Field[K2, V2], *RestT], column: K2, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], Field[K2, V2], *RestT]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], *RestT], column: K3, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], *RestT]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], *RestT], column: K4, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], *RestT]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], *RestT], column: K5, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], *RestT]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], *RestT], column: K6, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], *RestT]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], *RestT], column: K7, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], *RestT]: ...

    @overload
    def order_by(self: PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], Field[K8, V8], *RestT], column: K8, direction: OrderDirection='asc') -> PersonQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], Field[K8, V8], *RestT]: ...

class PetQuery(_Predicates[DatabaseExpressionBuilder[PetColumns, Literal['pet.id', 'id', 'pet.owner_id', 'owner_id'], Literal['pet.name', 'name'], Never, Literal['pet.species', 'species']], PetColumns, Literal['pet.id', 'id', 'pet.owner_id', 'owner_id'], Literal['pet.name', 'name'], Never, Literal['pet.species', 'species']], SingleTableQuery[Literal['pet'], PetColumns, PetScope, Literal['pet.id', 'pet.owner_id', 'owner_id'], Literal['pet.name', 'name'], Never, Literal['pet.species', 'species'], *FieldsT], Generic[*FieldsT,]):

    @overload
    def select(self, selections: Literal['pet.id', 'id']) -> PetQuery[Field[Literal['id'], int], *FieldsT]: ...

    @overload
    def select(self, selections: Literal['pet.owner_id', 'owner_id']) -> PetQuery[Field[Literal['owner_id'], int], *FieldsT]: ...

    @overload
    def select(self, selections: Literal['pet.name', 'name']) -> PetQuery[Field[Literal['name'], str], *FieldsT]: ...

    @overload
    def select(self, selections: Literal['pet.species', 'species']) -> PetQuery[Field[Literal['species'], Literal['cat', 'dog', 'hamster']], *FieldsT]: ...

    @overload
    def select(self, selections: PetColumns | Sequence[PetColumns]) -> PetQuery[Field[str, object], *FieldsT]: ...

    @overload
    def select_as(self, source: Literal['pet.id', 'id', 'pet.owner_id', 'owner_id'], alias: AliasT) -> PetQuery[Field[AliasT, int], *FieldsT]: ...

    @overload
    def select_as(self, source: Literal['pet.name', 'name'], alias: AliasT) -> PetQuery[Field[AliasT, str], *FieldsT]: ...

    @overload
    def select_as(self, source: Literal['pet.species', 'species'], alias: AliasT) -> PetQuery[Field[AliasT, Literal['cat', 'dog', 'hamster']], *FieldsT]: ...

    @overload
    def select_as(self, source: PetColumns, alias: str) -> PetQuery[Field[str, object], *FieldsT]: ...

    @overload
    def order_by(self, column: PetColumns, direction: OrderDirection='asc') -> PetQuery[*FieldsT,]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], *RestT], column: K1, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], *RestT]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], Field[K2, V2], *RestT], column: K2, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], Field[K2, V2], *RestT]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], *RestT], column: K3, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], *RestT]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], *RestT], column: K4, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], *RestT]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], *RestT], column: K5, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], *RestT]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], *RestT], column: K6, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], *RestT]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], *RestT], column: K7, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], *RestT]: ...

    @overload
    def order_by(self: PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], Field[K8, V8], *RestT], column: K8, direction: OrderDirection='asc') -> PetQuery[Field[K1, V1], Field[K2, V2], Field[K3, V3], Field[K4, V4], Field[K5, V5], Field[K6, V6], Field[K7, V7], Field[K8, V8], *RestT]: ...

class DatabaseClient(SchemaClient):

    @overload
    def select_from(self, table: Literal['person']) -> PersonQuery[()]: ...

    @overload
    def select_from(self, table: Literal['pet']) -> PetQuery[()]: ...

class DatabaseSchema(SchemaDefinition):
    person: PersonTable
    pet: PetTable

    @classmethod
    def connect(cls, *, dialect: Dialect, plugins: tuple[QueryPlugin, ...]=()) -> DatabaseClient: ...
