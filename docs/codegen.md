# Code generation

`pysely codegen` turns annotated schema classes into a typed query interface.
Your schema module stays the single source of truth; the generated module is a
build artifact you never edit by hand.

```bash
pysely codegen schema.py --output db.py
```

## Why a generator is needed

Kysely gets its type safety from TypeScript features Python does not have.
Given a schema type, TypeScript can compute the union of its key names with
`keyof` and look up a value type by key with an indexed access type. Python has
no equivalent, so there is no way to turn this:

```python
class PetTable:
    species: Literal["cat", "dog", "hamster"]
```

into `Literal["species", "pet.species"]` at the type level.

For a checker to reject `select("speces")`, the literal has to exist in a real
annotation. Mypy can synthesise one through a plugin, but Pyright — and
therefore Pylance and VS Code — has no plugin interface by design. Writing the
annotations to a file is the only mechanism every checker can read.

## What the generator reads

It parses the schema module with `ast`. It does not import it, execute it, or
connect to a database, so running it is fast and has no side effects.

```python
# schema.py
from datetime import date, datetime
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
    name: str
    species: Literal["cat", "dog", "hamster"]
    birth_date: date | None


class DatabaseSchema:
    person: PersonTable
    pet: PetTable
```

The database class is the one whose annotations are all other classes in the
same module. Every other referenced class is a table.

## What it writes

A `Database` class and a `DatabaseQuery` class carrying one overload per column,
plus `Literal` aliases for the column names in scope for each table.

```python
# db.py, generated
from db import Database

db = Database(dialect=dialect)

query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .where("first_name", "=", "Jennifer")
    .where("species", "=", "hamster")
    .select("first_name")
    .select_as("pet.name", "pet_name")
)
```

Both checkers reject an unknown table, an unknown column, a column belonging to
a table you have not joined, and a value whose type does not match its column.
Result keys stay typed: the query above executes to
`list[dict[Literal["first_name", "pet_name"], str]]`.

A bare column name is only generated when it is unambiguous. In the schema above
`id` exists on both tables, so only `person.id` and `pet.id` are offered, while
`species` is available bare because it appears once.

## Keeping the output current

The generated module is committed so editors work without a build step. Three
mechanisms keep it honest.

`--check` exits non-zero when the output is missing or stale, and prints the
command that fixes it:

```bash
pysely codegen schema.py --output db.py --check
```

Wire that into CI so a schema change cannot merge without its regenerated
interface:

```yaml
- run: pysely codegen schema.py --output db.py --check
```

And regenerate automatically on commit:

```yaml
repos:
  - repo: https://github.com/mylesmmurphy/pysely
    rev: v0.1.0.dev0
    hooks:
      - id: pysely-codegen
        args: [schema.py, --output, db.py]
```

## Runtime behaviour is separate

The generated module changes what checkers see, not what happens at runtime.
`Pysely(schema=DatabaseSchema, dialect=...)` validates table and column names
from the same classes whether or not you run the generator, and queries written
against the plain client still compile and execute. Without the generated
module you get that runtime validation and no static checking.

## Limitations

Value completion is broader than value checking. After a join, an editor may
offer literal values from any joined table at the `where()` value position,
because Pyright gathers completions from every applicable overload without
narrowing on the column argument you already typed. Choosing a value that does
not belong to the column is still reported as an error; only the suggestion list
is wider than it should be.

Database introspection is not implemented. Schema classes are written by hand
until `pysely introspect` ships.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Schema and typing](typing.md){ .md-button }
[Dialects →](dialects.md){ .md-button .md-button--primary }

</nav>
