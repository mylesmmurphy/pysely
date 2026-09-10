# Getting started

## Install

Install the development release with the driver extra for your database:

=== "uv"

    ```bash
    uv add --prerelease allow "pysely[sqlite]"
    ```

=== "pip"

    ```bash
    pip install --pre "pysely[sqlite]"
    ```

Use `postgres` or `mysql` instead of `sqlite` for those databases. Pysely is
currently a pre-alpha development release.

## Define your database

Use one annotated class per table and a database class mapping table names to
those types. These definitions drive runtime column validation.

```python
from datetime import datetime
from typing import Literal


class UserTable:
    id: int
    email: str
    display_name: str | None
    role: Literal["admin", "member"]
    verified: bool
    created_at: datetime


class Database:
    users: UserTable
```

## Connect and query

=== "SQLite"

    ```python
    import aiosqlite

    from pysely import SqliteDialect

    database = await aiosqlite.connect("app.db", isolation_level=None)
    dialect = SqliteDialect(database=database)
    ```

=== "PostgreSQL"

    ```python
    import asyncpg

    from pysely import PostgresDialect

    pool = await asyncpg.create_pool("postgresql://user:password@localhost/app")
    dialect = PostgresDialect(pool=pool)
    ```

=== "MySQL"

    ```python
    import asyncmy

    from pysely import MysqlDialect

    pool = await asyncmy.create_pool(
        host="127.0.0.1",
        user="app",
        password="secret",
        db="app",
        autocommit=True,
    )
    dialect = MysqlDialect(pool=pool)
    ```

Pass the selected dialect to Pysely:

```python
from pysely import Pysely


async with Pysely(schema=Database, dialect=dialect) as db:
    rows = await (
        db.select_from("users")
        .select(["id", "email"])
        .where("email", "=", "ada@example.com")
        .execute()
    )
```

Pysely passes values to the driver separately from generated SQL.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Home](index.md){ .md-button }
[Queries →](queries.md){ .md-button .md-button--primary }

</nav>
