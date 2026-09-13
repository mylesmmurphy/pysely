# Type generation

`pysely typgen` generates only an adjacent `.pyi` type stub. It does not generate
a runtime Python module, query implementation, or database class implementation.
Python never loads this stub: your handwritten schema and Pysely's shared runtime
are all execution needs. The stub can be omitted from a runtime-only deployment.

The stub can still be large for a large schema; that affects type-checking and
editor performance, not runtime imports. See [typing limits](typing.md).

## Define tables and schema

```python
# dbschema.py — handwritten
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

## Generate types

```sh
pysely typgen dbschema.py
pysely typgen dbschema.py --check  # CI: fail if missing or stale
```

This writes `dbschema.pyi`; it never overwrites `dbschema.py`. An explicit
`--output` must name the same adjacent stub. Generation parses the schema without
importing it or connecting to a database. Commit both files.

## Configure the client separately

```python
# db.py — handwritten
from .dbschema import DatabaseSchema

db = DatabaseSchema.connect(dialect=dialect)
```

Supply a Pysely dialect with your driver connection or pool. Plugins can be
passed with `plugins=(...)`. The schema is independent of the dialect.

```python
from .db import db

query = (
    db.select_from("person")
    .left_join("pet", "person.id", "pet.owner_id")
    .where("person.id", ">", 0)
    .select("person.id")
    .select_as("pet.name", "pet_name")
)
row = await query.execute_take_first_or_throw()
# row["id"]: int; row["pet_name"]: str | None
```

Joins and projections are ordinary Python calls, not typgen declarations.

## Runtime versus typing

Python imports `dbschema.py`; mypy/Pyright automatically prefer `dbschema.pyi`.
The stub replaces the module's typing interface, so it repeats table declarations.
No generated file is required at runtime. Shared Pysely code handles SQL, rows,
transactions and connection ownership. Schema metadata still exists at runtime.

Generated query/client names exist only for annotations. Import those under
`TYPE_CHECKING`, with postponed annotations; do not instantiate or runtime-check
them. Import `DatabaseSchema` normally.

Predicates use shared generics, results use flat field packs, and exact `select`
still uses per-column overloads. See [typing limits](typing.md) and
[connection setup](getting-started.md).
