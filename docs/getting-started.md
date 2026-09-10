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
those types. These definitions drive runtime column validation.

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

The [typing guide](typing.md) describes the standard-editor generated interface
now under development and the optional mypy checks available today. Try query
compilation in the [playground](playground.md).
