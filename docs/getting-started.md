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
those types. This is the only file you write by hand.

```python
# tables.py
from datetime import datetime
from typing import Literal


class UserTable:
    id: int
    email: str
    display_name: str | None
    role: Literal["admin", "member"]
    verified: bool
    created_at: datetime


class DatabaseSchema:
    users: UserTable
```

## Generate the typed client

Run the generator once, and again whenever the schema changes:

```bash
pysely codegen tables.py --output schema.py
```

`schema.py` is one self-contained module: your table classes, now typed.
Commit it. See [Code generation](codegen.md).

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

Pass the generated schema and the dialect to Pysely:

```python
from schema import schema
from pysely import Database


db = Database(schema=schema, dialect=dialect)
rows = await (
    db.select_from("users")
    .select("id")
    .select("email")
    .where("email", "=", "ada@example.com")
    .execute()
)
```

`rows[0]["id"]` is `int`, `rows[0]["email"]` is `str`, and `rows[0]["name"]`
is an editor error, as is a misspelled column or a wrong value type. Chain one
`.select()` per column; the list form compiles but reads keys as `object`.

Pysely passes values to the driver separately from generated SQL.

### Without generation

The same call with the hand-written `tables.DatabaseSchema` runs the same
queries with runtime name validation only. No static checking; rows are
`dict[str, object]`.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Home](index.md){ .md-button }
[Queries →](queries.md){ .md-button .md-button--primary }

</nav>
