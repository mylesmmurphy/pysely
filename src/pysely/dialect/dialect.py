from __future__ import annotations

from dataclasses import dataclass

from pysely.dialect.mysql import MysqlDriver, MysqlPoolProvider
from pysely.dialect.postgres import PostgresDriver, PostgresPoolProvider
from pysely.dialect.sqlite import SqliteDatabaseProvider, SqliteDriver
from pysely.driver import Driver
from pysely.query_compiler import BindingProfile, QueryCompiler


@dataclass(frozen=True, slots=True)
class Dialect:
    binding_profile: BindingProfile
    driver: Driver | None = None

    def create_query_compiler(self) -> QueryCompiler:
        return QueryCompiler(self.binding_profile)


class PostgresDialect(Dialect):
    def __init__(self, *, pool: PostgresPoolProvider) -> None:
        driver = PostgresDriver(pool)
        super().__init__(BindingProfile("postgres-asyncpg", "${position}"), driver)


class MysqlDialect(Dialect):
    def __init__(self, *, pool: MysqlPoolProvider) -> None:
        driver = MysqlDriver(pool)
        profile = BindingProfile(
            "mysql-asyncmy", "%s", "`", "`", None, supports_full_join=False
        )
        super().__init__(profile, driver)


class SqliteDialect(Dialect):
    def __init__(self, *, database: SqliteDatabaseProvider) -> None:
        driver = SqliteDriver(database)
        super().__init__(BindingProfile("sqlite-aiosqlite", "?"), driver)


class MssqlDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        profile = BindingProfile(
            "mssql-aioodbc", "?", "[", "]", "output", limit_style="fetch"
        )
        super().__init__(profile, driver)


class PGliteDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        super().__init__(BindingProfile("pglite", "${position}"), driver)
