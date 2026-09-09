from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from pysely.driver import Driver
from pysely.query_compiler import BindingProfile, QueryCompiler


@dataclass(frozen=True, slots=True)
class Dialect:
    binding_profile: BindingProfile
    driver: Driver | None = None

    def create_query_compiler(self) -> QueryCompiler:
        return QueryCompiler(self.binding_profile)


class PostgresDialect(Dialect):
    def __init__(
        self,
        *,
        pool: object | None = None,
        dsn: str | None = None,
        owns_pool: bool | None = None,
        driver: Driver | None = None,
    ) -> None:
        if driver and (pool is not None or dsn is not None):
            raise ValueError("Pass a PostgreSQL driver or pool configuration, not both")
        if driver is None and (pool is not None or dsn is not None):
            from pysely.dialect.postgres import PostgresDriver, PostgresPoolLike

            driver = PostgresDriver(
                pool=cast(PostgresPoolLike | None, pool),
                dsn=dsn,
                owns_pool=owns_pool,
            )
        super().__init__(BindingProfile("postgres-asyncpg", "${position}"), driver)


class MysqlDialect(Dialect):
    def __init__(
        self,
        *,
        pool: object | None = None,
        host: str | None = None,
        user: str | None = None,
        password: str = "",
        database: str | None = None,
        owns_pool: bool | None = None,
        driver: Driver | None = None,
    ) -> None:
        settings = (host, user, database)
        if driver and (
            pool is not None or any(value is not None for value in settings)
        ):
            raise ValueError("Pass a MySQL driver or pool configuration, not both")
        if driver is None and (
            pool is not None or any(value is not None for value in settings)
        ):
            from pysely.dialect.mysql import MysqlDriver, MysqlPoolLike

            driver = MysqlDriver(
                pool=cast(MysqlPoolLike | None, pool),
                host=host,
                user=user,
                password=password,
                database=database,
                owns_pool=owns_pool,
            )
        profile = BindingProfile("mysql-asyncmy", "%s", "`", "`", None)
        super().__init__(profile, driver)


class SqliteDialect(Dialect):
    def __init__(self, database: str | None = None) -> None:
        driver = None
        if database is not None:
            from pysely.dialect.sqlite import SqliteDriver

            driver = SqliteDriver(database)
        super().__init__(BindingProfile("sqlite-aiosqlite", "?"), driver)


class MssqlDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        profile = BindingProfile("mssql-aioodbc", "?", "[", "]", "output")
        super().__init__(profile, driver)


class PGliteDialect(Dialect):
    def __init__(self, *, driver: Driver | None = None) -> None:
        super().__init__(BindingProfile("pglite", "${position}"), driver)
