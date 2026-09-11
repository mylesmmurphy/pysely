# Schema and typing

Two layers, one source of truth:

| Layer | Source | What it does |
| --- | --- | --- |
| Runtime | your schema classes | validates table and column names when a query is built |
| Static | `db.py`, generated from those classes | lets mypy and Pyright check queries and complete names |

No checker plugin. Both checkers read ordinary annotations.

## Runtime only

```python
class PersonTable:
    id: int
    first_name: str
    status: Literal["active", "inactive"]


class DatabaseSchema:
    person: PersonTable


db = Pysely(schema=DatabaseSchema, dialect=dialect)
rows = await db.select_from("person").select("first_name").execute()
```

Unknown names raise `InvalidQueryError` at query-build time. Nothing is
checked statically; rows are `dict[str, object]`.

## Static checking

Run [code generation](codegen.md) and import the result:

```bash
pysely codegen schema.py --output db.py
```

```python
from db import DatabaseSchema
from pysely import Database

db = Database(schema=DatabaseSchema, dialect=dialect)
```

| Capability | Status |
| --- | --- |
| Table and column completion, before and after inner joins | Yes |
| Unknown or unjoined columns | Error |
| `.where()` values checked against the column type | Yes |
| Result keys from chained `.select()` / `.select_as()` | Literal keys |
| Result keys from `.select([...])` lists | `dict[str, object]` |
| Typed string writes | Not yet |
| Outer-join nullability | Not yet |
| PyCharm | Not verified |

## Rules

- Chain one `.select()` per column to keep result keys typed.
- Qualify column names that exist on more than one table (`person.id`).
- `.select_as("pet.name", "pet_name")` keeps the alias typed; the string form
  `"pet.name as pet_name"` compiles but is untyped.
- Rows are dicts: `row["first_name"]`, not `row.first_name`.

## Diagnostics

A wrong argument gets an argument-sized error. The failing call also gets a
call-sized error, because the fluent chain is the call's receiver.

Pyright's `strict` mode adds "type of X is unknown" errors across the rest of
the chain after one failure. The playground uses `standard`, Pyright's default,
which does not. Pick `standard` in Pylance to match.

Value completion after a join is a superset: an editor may offer literals from
any joined table at the `where()` value position. Wrong values are still
errors.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Queries](queries.md){ .md-button }
[Code generation →](codegen.md){ .md-button .md-button--primary }

</nav>
