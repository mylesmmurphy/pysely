# Getting started

## Install

These docs track the repository's `main` branch, including the new `typgen`
command. Install that source with the driver extra for your database:

=== "uv"

    ```bash
    uv add "pysely[sqlite] @ git+https://github.com/mylesmmurphy/pysely.git@main"
    ```

=== "pip"

    ```bash
    pip install "pysely[sqlite] @ git+https://github.com/mylesmmurphy/pysely.git@main"
    ```

Use `postgres` or `mysql` instead of `sqlite` for those databases. Pysely is
currently a pre-alpha development release.

## Define your database

Use one annotated class per table and a database class mapping table names to
those types. Keep schema definitions separate from connection setup.

```python
# dbschema.py
from datetime import datetime
from typing import Literal
from pysely import SchemaDefinition


class UserTable:
    id: int
    email: str
    display_name: str | None
    role: Literal["admin", "member"]
    verified: bool
    created_at: datetime


class DatabaseSchema(SchemaDefinition):
    users: UserTable
```

## Generate the typed client

Run the generator once, and again whenever the schema changes:

```bash
pysely typgen dbschema.py
```

`dbschema.pyi` is an adjacent type-only interface. Commit it alongside your
handwritten `dbschema.py`. See [Type generation](typgen.md).

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

Create the connected client in your application’s `db.py`:

```python
from dbschema import DatabaseSchema


db = DatabaseSchema.connect(dialect=dialect)
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

Removing the stub does not change runtime behavior. The same handwritten
schema and shared runtime still validate names and execute queries, but the
schema-specific static checks are unavailable.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Home](index.md){ .md-button }
[Queries →](queries.md){ .md-button .md-button--primary }

</nav>
