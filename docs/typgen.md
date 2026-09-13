# Type generation

`pysely typgen` generates **only a `.pyi` type stub**.
There is no generated runtime module, query implementation, or database implementation.

Python never loads the stub. You can leave it out of a runtime-only deployment.

## Three files, three jobs

| File | Who writes it? | Purpose |
| --- | --- | --- |
| `dbschema.py` | You | Table and column declarations |
| `dbschema.pyi` | `pysely typgen` | Editor completion and static checks |
| `db.py` | You | Dialect and connection setup |

Keep application logic outside the schema module. The generator reads declarations
without importing your code or connecting to a database.

## 1. Define the schema

```python
# dbschema.py
from pysely import SchemaDefinition


class PersonTable:
    id: int
    name: str


class PetTable:
    id: int
    owner_id: int
    name: str


class DatabaseSchema(SchemaDefinition):
    person: PersonTable
    pet: PetTable
```

The schema describes existing SQL tables. It does not create them.

## 2. Generate the stub

```bash
pysely typgen dbschema.py
```

This writes `dbschema.pyi` beside `dbschema.py`.

- The handwritten source is never overwritten.
- An explicit `--output` must name that same adjacent stub.
- Commit both files and regenerate after schema edits.

## 3. Configure the database

```python
# db.py
import aiosqlite

from pysely import SqliteDialect
from dbschema import DatabaseSchema

db = DatabaseSchema.connect(
    dialect=SqliteDialect(
        database=lambda: aiosqlite.connect("app.db", isolation_level=None)
    )
)
```

This factory opens the connection lazily. Close the client with `await db.destroy()`
at application shutdown.

The schema is independent of the dialect. See [Dialects](dialects.md) for pool setup.

## Write queries normally

```python
from db import db

query = (
    db.select_from("person")
    .left_join("pet", "person.id", "pet.owner_id")
    .select("person.id")
    .select_as("pet.name", "pet_name")
)
```

A result's `"id"` is `int`; `"pet_name"` is `str | None`.
Write joins and selections in Python—no predefined query configuration.

## Check freshness in CI

```bash
pysely typgen dbschema.py --check
```

Exits nonzero if the stub is missing or stale. It does not rewrite files or
compare your declarations with a live database.

## Start from an existing database

`introspect` is a separate, optional scaffolding command:

```bash
pysely introspect --dialect sqlite --url app.db --output dbschema.py
pysely typgen dbschema.py
```

Unlike `typgen`, `introspect` writes a Python source file.
Choose a new output path; introspection overwrites an existing output file.

PostgreSQL and MySQL are also supported. Run `pysely introspect --help` for
connection options, type overrides, and unknown-type handling.

## What goes in the stub?

It repeats table declarations and adds typed client and query interfaces.
mypy and Pyright read these instead of the module's runtime annotations.

Import `DatabaseSchema` normally. Generated query classes are annotation-only;
see [query helpers](typing.md#advanced-query-helpers) before importing them.

A large schema can still produce a large stub. That affects type checking and
editor speed, not runtime imports. See [typing limits and performance](typing.md).

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Schema and typing](typing.md){ .md-button }
[Dialects →](dialects.md){ .md-button .md-button--primary }

</nav>
