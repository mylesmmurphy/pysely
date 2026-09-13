# Dialects

A dialect chooses SQL syntax and connects Pysely to a database driver.
You provide the connection or pool; Pysely does not accept a URL directly.

Choose a database below. The install commands use `main`, matching these docs.
Run connection setup containing `await` inside your application's async startup.

=== "PostgreSQL"

    === "uv"

        ```bash
        uv add "pysely[postgres] @ git+https://github.com/mylesmmurphy/pysely.git@main"
        ```

    === "pip"

        ```bash
        pip install "pysely[postgres] @ git+https://github.com/mylesmmurphy/pysely.git@main"
        ```

    ```python
    import asyncpg

    from pysely import PostgresDialect


    pool = await asyncpg.create_pool("postgresql://user:password@localhost/app")
    dialect = PostgresDialect(pool=pool)
    ```

    Pysely acquires a pool connection for each query or connection scope.

    A factory can initialize the pool lazily:

    ```python
    async def create_pool():
        return await asyncpg.create_pool("postgresql://localhost/app")


    dialect = PostgresDialect(pool=create_pool)
    ```

=== "MySQL"

    === "uv"

        ```bash
        uv add "pysely[mysql] @ git+https://github.com/mylesmmurphy/pysely.git@main"
        ```

    === "pip"

        ```bash
        pip install "pysely[mysql] @ git+https://github.com/mylesmmurphy/pysely.git@main"
        ```

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

    Keep `autocommit=True`. Explicit Pysely transactions still commit or roll back as a unit.

=== "SQLite"

    === "uv"

        ```bash
        uv add "pysely[sqlite] @ git+https://github.com/mylesmmurphy/pysely.git@main"
        ```

    === "pip"

        ```bash
        pip install "pysely[sqlite] @ git+https://github.com/mylesmmurphy/pysely.git@main"
        ```

    ```python
    import aiosqlite

    from pysely import SqliteDialect


    database = await aiosqlite.connect("app.db", isolation_level=None)
    dialect = SqliteDialect(database=database)
    ```

    `isolation_level=None` enables autocommit. Use `":memory:"` instead of `"app.db"`
    for a temporary database.

## Create and close the client

Use the `dialect` from the selected tab:

```python
from dbschema import DatabaseSchema

async with DatabaseSchema.connect(dialect=dialect) as db:
    rows = await db.select_from("person").select("id").execute()
```

For a long-lived client, create it at startup and call `await db.destroy()` at shutdown.

Pysely closes the configured pool or connection. Do not give it a resource that
another part of your application must keep using after the client is destroyed.

## Database differences

| Database | Driver | Important boundary |
| --- | --- | --- |
| PostgreSQL | `asyncpg` | Connection pools supported |
| MySQL | `asyncmy` | No full join or `returning()` through this API |
| SQLite | `aiosqlite` | One configured connection |
| SQL Server / PGlite | No runtime adapter yet | Offline compilation only |

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Type generation](typgen.md){ .md-button }
[Project status →](project-status.md){ .md-button .md-button--primary }

</nav>
