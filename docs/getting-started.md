# Getting started

Run a typed query against an in-memory SQLite database. No database server needed.

Pysely is pre-alpha. These docs use `main`, not an older PyPI release.

## 1. Install

=== "uv"

    ```bash
    uv add "pysely[sqlite] @ git+https://github.com/mylesmmurphy/pysely.git@main"
    ```

=== "pip"

    ```bash
    pip install "pysely[sqlite] @ git+https://github.com/mylesmmurphy/pysely.git@main"
    ```

Using PostgreSQL or MySQL? See [Dialects](dialects.md).

## 2. Describe a table

Create `dbschema.py`:

```python
from pysely import SchemaDefinition


class PersonTable:
    id: int
    first_name: str


class DatabaseSchema(SchemaDefinition):
    person: PersonTable
```

`person` is the SQL table name. Its attributes describe column names and Python types.

These declarations do not create or migrate database tables.

## 3. Generate editor types

```bash
pysely typgen dbschema.py
```

This creates `dbschema.pyi`. Keep it beside `dbschema.py` and regenerate it after schema edits.

Only the stub is generated. Python never loads it; there is no generated runtime module.

## 4. Run a query

Create `db.py` beside `dbschema.py`:

```python
import asyncio

import aiosqlite

from pysely import SqliteDialect
from dbschema import DatabaseSchema


async def main() -> None:
    database = await aiosqlite.connect(":memory:", isolation_level=None)
    dialect = SqliteDialect(database=database)

    async with DatabaseSchema.connect(dialect=dialect) as db:
        # Demo setup only; real applications manage their own migrations.
        await database.execute(
            "create table person (id integer primary key, first_name text not null)"
        )
        await database.execute(
            "insert into person (id, first_name) values (?, ?)", (1, "Ada")
        )

        row = await (
            db.select_from("person")
            .select("id")
            .select("first_name")
            .where("first_name", "=", "Ada")
            .execute_take_first_or_throw()
        )
        print(row.to_dict())


asyncio.run(main())
```

Run `python db.py` (or `uv run python db.py`):

```text
{'id': 1, 'first_name': 'Ada'}
```

The `async with` block closes the database when it exits.

## What the editor knows

- `row["id"]` is `int`.
- `row["first_name"]` is `str`.
- An unselected key, misspelled column, or wrong filter value is a type error.

Use one `.select()` per column for precise result types. The list form returns `object` values.

## Next steps

- [Queries](queries.md): filtering, joins, writes, and transactions.
- [Schema and typing](typing.md): what is checked and what is not.
- [Type generation](typgen.md): file layout, CI, and existing databases.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Home](index.md){ .md-button }
[Queries →](queries.md){ .md-button .md-button--primary }

</nav>
