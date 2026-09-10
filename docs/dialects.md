# Dialects

Install only the driver needed by the application.

=== "PostgreSQL"

    === "uv"

        ```bash
        uv add --prerelease allow "pysely[postgres]"
        ```

    === "pip"

        ```bash
        pip install --pre "pysely[postgres]"
        ```

    ```python
    import asyncpg

    from pysely import PostgresDialect, Pysely


    pool = await asyncpg.create_pool("postgresql://user:password@localhost/app")
    db = Pysely[object](dialect=PostgresDialect(pool=pool))
    ```

    Pysely acquires connections from the provided pool and closes the pool when
    `db.destroy()` runs.

    A factory can initialize the pool lazily:

    ```python
    async def create_pool():
        return await asyncpg.create_pool("postgresql://localhost/app")


    db = Pysely[object](dialect=PostgresDialect(pool=create_pool))
    ```

=== "MySQL"

    === "uv"

        ```bash
        uv add --prerelease allow "pysely[mysql]"
        ```

    === "pip"

        ```bash
        pip install --pre "pysely[mysql]"
        ```

    ```python
    import asyncmy

    from pysely import MysqlDialect, Pysely


    pool = await asyncmy.create_pool(
        host="127.0.0.1",
        user="app",
        password="secret",
        db="app",
        autocommit=True,
    )
    db = Pysely[object](dialect=MysqlDialect(pool=pool))
    ```

    MySQL pools must have autocommit enabled. Pysely closes the pool when
    `db.destroy()` runs.

=== "SQLite"

    === "uv"

        ```bash
        uv add --prerelease allow "pysely[sqlite]"
        ```

    === "pip"

        ```bash
        pip install --pre "pysely[sqlite]"
        ```

    ```python
    import aiosqlite

    from pysely import Pysely, SqliteDialect


    database = await aiosqlite.connect("app.db", isolation_level=None)
    db = Pysely[object](dialect=SqliteDialect(database=database))
    ```

    SQLite databases must use autocommit. Use `async with` or call
    `await db.destroy()` to close the database.
