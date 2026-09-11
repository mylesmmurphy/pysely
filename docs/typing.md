# Schema and typing

Pysely has two layers. Annotated schema classes drive runtime validation, and a
generated module built from those same classes drives static checking. No
checker plugin is involved; both mypy and Pyright read ordinary annotations.

## Runtime schemas

Runtime schemas are annotated classes:

```python
from datetime import datetime
from typing import Literal


class PersonTable:
    id: int
    first_name: str
    nickname: str | None
    status: Literal["active", "inactive"]
    created_at: datetime


class DatabaseSchema:
    person: PersonTable


db = Pysely(schema=DatabaseSchema, dialect=PostgresDialect(pool=pool))
rows = await db.select_from("person").select(["id", "first_name"]).execute()
```

This validates table and column names when the query is built, and raises
`InvalidQueryError` for an unknown name or a column outside the query's scope.

Used on its own, this form is **not statically checked**. `select_from()` takes
a `str`, `where()` takes a `str` and an `object`, and the result type is the
conservative `dict[str, object]`. A misspelled column is a runtime error, not an
editor error.

## Static checking

Static checking comes from [code generation](codegen.md). The generator reads
the classes above and writes one self-contained module carrying those classes
and the literal types a checker needs:

```bash
pysely codegen schema.py --output db.py
```

```python
from db import Database

db = Database(dialect=PostgresDialect(pool=pool))

query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .where("first_name", "=", "Jennifer")
    .where("species", "=", "hamster")
    .select("first_name")
    .select_as("pet.name", "pet_name")
)
```

With the generated module in place:

| Capability | Status |
| --- | --- |
| Table-name completion and checking | Available |
| Column completion before and after inner joins | Available |
| Invalid and unjoined columns | Rejected |
| `.where()` comparison values | Checked against the column type |
| Result keys from chained `.select()` and `.select_as()` | Literal keys retained |
| Result keys from `.select([...])` lists and tuples | Conservative `dict[str, object]` |
| Runtime schema validation | Available, with or without generation |
| Typed string writes | Not implemented |
| Outer-join nullability | Not implemented |
| PyCharm support | Not verified |

Chain one `.select()` or `.select_as()` per column to keep result keys typed;
there is no fixed projection limit. Dynamic aliases and duplicate aliases fall
back to a broader mapping type.

A bare column name is generated only when it is unique across the whole schema.
If `id` exists on both `person` and `pet`, write `person.id` even in a query
that only touches `person`. The runtime is more lenient — it resolves a bare
name whenever it is unique in the current query scope — but a checker cannot
see scope, so the static rule is stricter to stay sound.

## Why generation rather than a plugin

Python's type system cannot derive `Literal["species"]` from a class annotated
with `species: ...`. It has no `keyof` and no indexed access types, so the
literals must exist in real annotations somewhere.

Mypy could synthesise them through a plugin, and earlier versions of Pysely
shipped one. Pyright has no plugin interface, so the same information had to be
generated anyway — which meant two implementations of one set of rules, able to
disagree with each other. The plugin has been removed. Generation serves both
checkers from one implementation, and the generated module is verified in CI.

## Editor diagnostics

Language servers may underline a larger fluent chain when a call fails, because
the chain is the call's receiver. Failed overloads and missing arguments can
also produce follow-on unknown-type errors. The invalid argument still receives
its own argument-sized diagnostic.

For a temporarily tighter diagnostic range, split the chain while locating an
error:

```python
query = db.select_from("person")
joined = query.inner_join("pet", "owner_id", "person.id")
filtered = joined.where("first_name", "=", "Jennifer")
selected = filtered.select("first_name")
```

Each variable keeps a distinct name because joins and projections change the
query's static type.

## Value completion after a join

After joining two tables, an editor may suggest literal values belonging to any
joined table at the `where()` value position, not only the column you named.
Pyright collects completions from every applicable overload without narrowing on
the column argument already typed, so the suggestion list is a superset.

Checking is unaffected: a value that does not belong to the column is reported
as an error. Only the suggestion list is wider than it should be.

## Syntax differences from Kysely

Pysely prefers `.select_as("pet.name", "pet_name")` for typed aliases. Python
typing cannot split an arbitrary `"pet.name as pet_name"` string into a source
type and a result key.

- Direct literal aliases retain key completion and value information.
- Dynamic or conflicting aliases use conservative result types.
- The single-string form compiles at runtime without the same static inference.

Results are dictionaries: use `row["first_name"]` for field access and key
completion. Dot access such as `row.first_name` is not supported. When selected
columns have different value types, the dictionary value type is their union.

The browser [playground](playground.md) runs Pysely for query compilation,
`pysely codegen` for the typed interface, and Pyright for editor intelligence.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Queries](queries.md){ .md-button }
[Code generation →](codegen.md){ .md-button .md-button--primary }

</nav>
