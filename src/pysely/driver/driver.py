from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from pysely.query_compiler import CompiledQuery

RowT = TypeVar("RowT")


@dataclass(frozen=True, slots=True)
class QueryResult(Generic[RowT]):
    rows: tuple[RowT, ...] = ()
    affected_rows: int | None = None
    changed_rows: int | None = None
    insert_id: object | None = None


class DatabaseConnection(Protocol):
    async def execute_query(
        self, query: CompiledQuery[object]
    ) -> QueryResult[dict[str, object]]: ...

    async def begin(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class Driver(Protocol):
    @property
    def binding_profile_name(self) -> str: ...

    async def init(self) -> None: ...

    async def acquire_connection(self) -> DatabaseConnection: ...

    async def release_connection(self, connection: DatabaseConnection) -> None: ...

    async def destroy(self) -> None: ...
