# Code generation

One command turns your schema classes into one module. Pass its schema class
to `Pysely.create`; nothing else is needed.

```
schema.py  ──  pysely codegen  ──▶  db.py  ──  Pysely.create(schema=…)  ──▶  typed client
(you write)                          (generated)
```

## 1. Write the schema

```python
# schema.py
from datetime import datetime
from typing import Literal


class PersonTable:
    id: int
    first_name: str
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
- Don't name a class `DatabaseClient` or `DatabaseQuery`; the output defines
  those.

## 2. Generate

```bash
pysely codegen schema.py --output db.py
```

`db.py` contains a copy of your schema classes, with `DatabaseSchema` now
carrying the typing, plus the client it builds. Commit it. `schema.py` is not
needed at runtime.

## 3. Query

```python
from db import DatabaseSchema
from pysely import Pysely

db = Pysely.create(schema=DatabaseSchema, dialect=dialect)

query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .where("species", "=", "hamster")
    .select("first_name")
    .select_as("pet.name", "pet_name")
)
```

`Pysely.create` returns the typed client named by the generated schema; for a
plain schema it returns an ordinary `Pysely`. mypy and Pyright now reject
unknown tables, unknown or unjoined columns, and values of the wrong type.
`rows[0]["pet_name"]` is typed.

## Keep it current

| When | Command |
| --- | --- |
| Schema changed | `pysely codegen schema.py --output db.py` |
| CI | `pysely codegen schema.py --output db.py --check` (fails if stale) |
| On commit | pre-commit hook `pysely-codegen` from this repo |

## Rules worth knowing

- **Chain `.select()` per column** for typed result keys.
  `.select(["a", "b"])` compiles but types rows as `dict[str, object]`.
- **Qualify shared column names.** If `id` exists on two tables, write
  `person.id`, even in a single-table query. The runtime is more lenient; the
  checker cannot see query scope.
- **Value suggestions after a join are a superset.** An editor may offer
  literals from any joined table at the `where()` value position. Wrong values
  are still errors.

## How it works

The generator parses `schema.py` with `ast`. It never imports it, never runs
it, and never touches a database. Output is deterministic and lint-clean.

Why generate at all: Python has no `keyof` or mapped types, so a checker can
only see `Literal["species"]` if that literal exists in a real annotation.
Pyright has no plugin interface, so writing the file is the only option that
works in every editor.

## Not yet

`pysely introspect` — writing `db.py` straight from a live database — is
planned.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Schema and typing](typing.md){ .md-button }
[Dialects →](dialects.md){ .md-button .md-button--primary }

</nav>
