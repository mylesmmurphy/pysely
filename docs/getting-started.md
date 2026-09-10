# Getting started

## Install

Install the development release with the driver extra for your database:

```bash
uv add --prerelease allow "pysely[sqlite]"
```

With pip:

```bash
pip install --pre "pysely[sqlite]"
```

Use `postgres` or `mysql` instead of `sqlite` for those databases. Pysely is
currently a pre-alpha development release.

## Define your database

Use one annotated class per table and a database class mapping table names to
those types. The same definitions drive runtime column validation and the mypy
plugin's scope and result inference.

```python
class UserTable:
    id: int
    email: str
    nickname: str | None


class Database:
    users: UserTable
```

## Connect and query

```python
import aiosqlite

from pysely import Pysely, SqliteDialect


database = await aiosqlite.connect("app.db", isolation_level=None)
async with Pysely(schema=Database, dialect=SqliteDialect(database=database)) as db:
    rows = await (
        db.select_from("users")
        .select(["id", "email"])
        .where("email", "=", "ada@example.com")
        .execute()
    )
```

All values are passed separately from the generated SQL as driver parameters.

Enable [the mypy plugin](typing.md) for string-reference checks and selected-row
inference. Try the same API with editor suggestions in the [playground](playground.md).
