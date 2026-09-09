from typing import Never

from pysely import MysqlDialect, PostgresDialect, SqliteDialect


async def _unavailable_database() -> Never:
    raise RuntimeError("This test dialect only compiles queries")


def postgres_dialect() -> PostgresDialect:
    return PostgresDialect(pool=_unavailable_database)


def mysql_dialect() -> MysqlDialect:
    return MysqlDialect(pool=_unavailable_database)


def sqlite_dialect() -> SqliteDialect:
    return SqliteDialect(database=_unavailable_database)
