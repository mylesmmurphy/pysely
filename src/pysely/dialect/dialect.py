from __future__ import annotations

from dataclasses import dataclass

from pysely.driver import Driver
from pysely.query_compiler import BindingProfile, QueryCompiler


@dataclass(frozen=True, slots=True)
class Dialect:
    binding_profile: BindingProfile
    driver: Driver | None = None

    def create_query_compiler(self) -> QueryCompiler:
        return QueryCompiler(self.binding_profile)


class PostgresDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        super().__init__(BindingProfile("postgres-asyncpg", "${position}"), driver)


class MysqlDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        super().__init__(BindingProfile("mysql-asyncmy", "%s", "`", "`"), driver)


class SqliteDialect(Dialect):
    def __init__(self, database: str | None = None) -> None:
        driver = None
        if database is not None:
            from pysely.dialect.sqlite import SqliteDriver

            driver = SqliteDriver(database)
        super().__init__(BindingProfile("sqlite-aiosqlite", "?"), driver)


class MssqlDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        super().__init__(BindingProfile("mssql-aioodbc", "?", "[", "]"), driver)


class PGliteDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        super().__init__(BindingProfile("pglite", "${position}"), driver)
