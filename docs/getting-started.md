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
# schema.py
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
pysely codegen schema.py --output db.py
```

`db.py` is a single self-contained module. It carries your schema classes and
a `Database` client whose methods know every table, column, and value type, so
mypy and Pyright — and therefore Pylance in VS Code — check your queries and
complete column names. Commit it; editors need no build step. See
[Code generation](codegen.md) for `--check` and the pre-commit hook.

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

Pass the selected dialect to the generated client:

```python
from db import Database


db = Database(dialect=dialect)
rows = await (
    db.select_from("users")
    .select("id")
    .select("email")
    .where("email", "=", "ada@example.com")
    .execute()
)
```

`rows` is typed as `list[dict[Literal["id", "email"], int | str]]`. A
misspelled column, a column from a table you have not joined, or a value of the
wrong type — `.where("role", "=", "owner")` when `role` is
`Literal["admin", "member"]` — is an editor error before the query runs.

Chain one `.select()` per column to keep result keys typed. The list form,
`.select(["id", "email"])`, compiles to the same SQL but types its rows as
`dict[str, object]`.

Pysely passes values to the driver separately from generated SQL.

### Without the generated client

The schema classes alone give runtime validation. `Pysely(schema=DatabaseSchema,
dialect=dialect)` accepts the same queries and raises `InvalidQueryError` for an
unknown table or column when the query is built — but nothing is checked
statically, and results are `dict[str, object]`.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Home](index.md){ .md-button }
[Queries →](queries.md){ .md-button .md-button--primary }

</nav>
