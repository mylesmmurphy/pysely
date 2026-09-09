# Dialects

Install only the driver needed by the application.

## PostgreSQL

```python
import asyncpg

from pysely import PostgresDialect, Pysely


pool = await asyncpg.create_pool("postgresql://user:password@localhost/app")
db = Pysely[object](dialect=PostgresDialect(pool=pool))
```

Install with `uv sync --extra postgres`. Pysely acquires connections from the
provided pool and closes the pool when `db.destroy()` runs.

## MySQL

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

Install with `uv sync --extra mysql`. MySQL pools must have autocommit enabled.
Pysely closes the pool when `db.destroy()` runs.

## SQLite

```python
import aiosqlite

from pysely import Pysely, SqliteDialect


database = await aiosqlite.connect("app.db", isolation_level=None)
db = Pysely[object](dialect=SqliteDialect(database=database))
```

Install with `uv sync --extra sqlite`. SQLite databases must use autocommit.
Use `async with` or call `await db.destroy()` to close the database.

Each dialect also accepts an async factory for lazy initialization:

```python
async def create_pool():
    return await asyncpg.create_pool("postgresql://localhost/app")


db = Pysely[object](dialect=PostgresDialect(pool=create_pool))
```
