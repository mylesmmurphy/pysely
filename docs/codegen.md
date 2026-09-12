# Code generation

One command turns your table classes into one typed schema module. Pass its
`schema` to `Database`; nothing else is needed.

```
tables.py  ──  pysely codegen  ──▶  schema.py  ──  Database(schema=…)  ──▶  typed client
(you write)                          (generated)
```

## 1. Write the tables

```python
# tables.py
from datetime import datetime
from typing import Literal


class PersonTable:
    id: int
    first_name: str
    last_name: str | None
    status: Literal["active", "inactive"]
    created_at: datetime


class PetTable:
    id: int
    owner_id: int
    species: Literal["cat", "dog", "hamster"]


class DatabaseSchema:
    person: PersonTable
    pet: PetTable
```

- One class per table. The database class maps table names to those classes.
- `X | None`, `Optional[X]` and `Union[X, None]` all mean nullable.
- Don't name a class `DatabaseClient`, `DatabaseQuery`, `DatabaseRow`,
  `DatabaseExpressionBuilder` or `TableName`; the output defines those.

## 2. Generate

```bash
pysely codegen tables.py --output schema.py
```

`schema.py` contains a copy of your table classes, the `schema` to pass to
`Database`, and the typed query, row and expression classes. Commit it.
`tables.py` is not needed at runtime.

## 3. Query

```python
from schema import schema
from pysely import Database

db = Database(schema=schema, dialect=dialect)

query = (
    db.select_from("person")
    .left_join("pet", "owner_id", "person.id")
    .where("status", "=", "active")
    .select("person.id")
    .select("first_name")
    .select_as("pet.species", "kind")
)
row = await query.execute_take_first_or_throw()
row["id"]       # int
row["kind"]     # Literal["cat", "dog", "hamster"] | None  (left join)
row["missing"]  # error
```

`Database` returns the typed client named by the generated schema; for a
plain schema it returns an ordinary `Pysely`. See [Schema and typing](typing.md)
for what is checked.

## Keep it current

| When | Command |
| --- | --- |
| Tables changed | `pysely codegen tables.py --output schema.py` |
| CI | `pysely codegen tables.py --output schema.py --check` (fails if stale) |
| On commit | pre-commit hook `pysely-codegen` from this repo |

## How it works

The generator parses `tables.py` with `ast`. It never imports it, never runs
it, and never touches a database. Output is deterministic and lint-clean.

The typed classes carry one overload per column and live under
`TYPE_CHECKING`; a slim runtime twin of each class sits beside them, so import
time does not grow with the schema.

Why generate at all: Python has no `keyof` or mapped types, so a checker can
only see `Literal["species"]` if that literal exists in a real annotation.
Pyright has no plugin interface, so writing the file is the only option that
works in every editor.

## From a live database

```bash
pysely introspect --dialect postgres --url postgresql://app@localhost/app -o tables.py
pysely codegen tables.py --output schema.py
```

`introspect` reads the catalog (SQLite file path, PostgreSQL DSN with
`--schema`, or `mysql://user:pass@host:port` with `--schema` as the
database) and writes the same `tables.py` you would write by hand, then
stops: connection details never reach the output. Nullability becomes
`X | None`; enum columns become `Literal[...]`; defaults, generated columns,
primary and foreign keys are recorded as comments. A SQL type with no Python
mapping fails the run; pass `--override table.column=Type` for it, or
`--unknown object` to accept `object`. Edit the file freely afterwards.

## Limits

- Pyright stops analysing a module above roughly 15,000 method definitions;
  `codegen` fails near that point (about 80 tables of 17 columns). Split
  large databases into several database classes, one generated module each.
- The generated module carries `# mypy: ignore-errors`, because mypy's
  overload-overlap check is quadratic in the overload count. Your own code is
  still checked; the generator's output is checked in Pysely's CI.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Schema and typing](typing.md){ .md-button }
[Dialects →](dialects.md){ .md-button .md-button--primary }

</nav>
