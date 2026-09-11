# Code generation

`pysely codegen` turns your annotated schema classes into a single generated
module that contains everything Pysely needs. You write one file, run one
command, and import one module.

## The process

**1. Write your schema.** One annotated class per table, plus a class that maps
table names to those classes. This is the only file you maintain by hand.

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
module. It cannot be named `Database` or `DatabaseQuery`, because the generated
module defines those.

**2. Generate.** One command, one output file.

```bash
pysely codegen schema.py --output db.py
```

**3. Import the generated module.** It is self-contained: it carries a copy of
your schema classes and the typed query interface built from them. Your
application imports `db.py` and nothing else. `schema.py` is not needed at
runtime and does not have to be on the import path.

```python
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

That is the whole process. Edit `schema.py`, rerun the command, and `db.py`
follows.

## What you get

With the generated module, both mypy and Pyright reject an unknown table, an
unknown column, a column belonging to a table you have not joined, and a value
whose type does not match its column. Result keys stay typed: the query above
executes to `list[dict[Literal["first_name", "pet_name"], str]]`.

Column names are offered qualified and, when unique across the whole schema,
bare. In the schema above `id` exists on both tables, so write `person.id` or
`pet.id` even in a single-table query, while `species` is offered bare because
it appears once. The runtime resolves bare names by query scope and is more
lenient; the static rule is stricter because a checker cannot see scope.

Chain one `.select()` per column to keep result keys typed. The list form
`.select(["a", "b"])` compiles identically but types rows as `dict[str, object]`.

## Why generation is needed

Kysely gets its type safety from TypeScript features Python does not have.
TypeScript can compute the union of a type's key names with `keyof` and look a
value type up by key with an indexed access type. Python cannot turn

```python
class PetTable:
    species: Literal["cat", "dog", "hamster"]
```

into `Literal["species", "pet.species"]` at the type level. For a checker to
reject `select("speces")`, the literal has to exist in a real annotation.
Writing those annotations to a file is the only mechanism every checker can
read — mypy could synthesise them through a plugin, but Pyright, and therefore
Pylance and VS Code, has no plugin interface by design.

## How the generator works

It parses `schema.py` with `ast`. It never imports the file, never executes
it, and never connects to a database, so it is fast and has no side effects.
It re-emits your classes verbatim into the output, then writes one overload per
column and `Literal` aliases for the column names in scope for each table.

The output is deterministic, formatted, and lint-clean, and is meant to be
committed so editors work without a build step.

## Keeping the output current

`--check` exits non-zero when the output is missing or stale and prints the
command that fixes it:

```bash
pysely codegen schema.py --output db.py --check
```

Use it in CI so a schema change cannot merge without its regenerated module:

```yaml
- run: pysely codegen schema.py --output db.py --check
```

And regenerate automatically on commit with the published pre-commit hook:

```yaml
repos:
  - repo: https://github.com/mylesmmurphy/pysely
    rev: v0.1.0.dev0
    hooks:
      - id: pysely-codegen
        args: [schema.py, --output, db.py]
```

## Without generation

`Pysely(schema=DatabaseSchema, dialect=...)` validates table and column names
at runtime from the same classes, and queries compile and execute unchanged.
What you lose is static checking: `select_from()` takes a `str`, `where()`
takes a `str` and an `object`, and results are `dict[str, object]`.

## Limitations

Value completion is broader than value checking. After a join, an editor may
offer literal values from any joined table at the `where()` value position,
because Pyright gathers completions from every applicable overload without
narrowing on the column argument already typed. Choosing a value that does not
belong to the column is still reported as an error; only the suggestion list is
wider than it should be.

Database introspection is not implemented. When it ships, `pysely introspect`
will write the same single module directly from a live database, with no
hand-written `schema.py` in between.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Schema and typing](typing.md){ .md-button }
[Dialects →](dialects.md){ .md-button .md-button--primary }

</nav>
