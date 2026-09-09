# Dialects

Install only the driver needed by the application.

## PostgreSQL

```python
from pysely import PostgresDialect, Pysely

db = Pysely[object](
    dialect=PostgresDialect(dsn="postgresql://user:password@localhost/app")
)
```

Install with `uv sync --extra postgres`. An existing `asyncpg` pool can be
passed as `pool=`. Borrowed pools remain open unless `owns_pool=True` is set.

## MySQL

```python
from pysely import MysqlDialect, Pysely

db = Pysely[object](
    dialect=MysqlDialect(
        host="127.0.0.1",
        user="app",
        password="secret",
        database="app",
    )
)
```

Install with `uv sync --extra mysql`. An existing `asyncmy` pool can be passed
as `pool=`. Borrowed MySQL pools must have autocommit enabled.

## SQLite

```python
from pysely import Pysely, SqliteDialect

db = Pysely[object](dialect=SqliteDialect("app.db"))
```

Install with `uv sync --extra sqlite`. Use `async with` or call
`await db.destroy()` to close owned resources.
