# Schema and typing

Pysely checks table names, column names, filter values, and selected result types.
Generate a stub with [`pysely typgen`](typgen.md) to enable these checks.

| When | What runs |
| --- | --- |
| In your editor or CI | mypy/Pyright reads `dbschema.pyi` |
| When your app runs | Python reads `dbschema.py` and uses shared Pysely code |

The stub is never imported by Python. No checker plugin is needed.

## Exact result types

“Exact” means the checker knows both the selected key and its value type.

```python
row = await (
    db.select_from("person")
    .select("id")
    .execute_take_first_or_throw()
)

person_id = row["id"]  # int
# row["first_name"]   # type error: not selected
```

Use one `select` call per column. With `select(["id", "first_name"])`,
column names are checked, but result values are typed as `object`.

## Column names and scope

A column is “in scope” if its table is part of the query.

- Before a join, `"id"` and `"person.id"` both work.
- After a join, qualify names shared by multiple schema tables: `"person.id"`.
- Columns from tables you have not joined are rejected.

The static rule is conservative: after a join, a bare name must be unique in
the whole schema, not just among the joined tables.

## Aliases

```python
query = db.select_from("person").select_as("id", "person_id")
```

The result has a `"person_id"` key of type `int`.
Use a literal alias; dynamic aliases have [checker-specific limits](#dynamic-aliases).

The combined string `"id as person_id"` is supported at runtime, not for exact static typing.

## Nullable values

Declare a nullable column as `str | None`, `int | None`, or another optional type.

| Join | Result typing |
| --- | --- |
| Inner | Keeps declared column types |
| Left | Joined-table values may also be `None` |
| Right or full | Every value may be `None` (conservative) |

Use `where("column", "is", None)` for SQL `NULL`, not `= None`.
See [filter operators](queries.md#filter-rows) for accepted values.

## Working with rows

Typed reads return `FlatRow`, an immutable mapping.

- `row["id"]`: read a known key with its exact type.
- `row.get("missing")`: unknown keys are allowed, as with ordinary mappings.
- `row.to_dict()`: copy all fields into a `dict[str, object]`.

Exact lookup covers the **64 most recent selections**. Use `to_dict()` for
older fields. The regression suite checks every type in a mixed 50-field result.

Avoid duplicate result names. Runtime validation rejects duplicate output names;
static alias inference alone does not guarantee a valid SQL result.

## Current limits

| Feature | Boundary |
| --- | --- |
| String-based writes | No schema-specific static checking of keys or values yet |
| Table aliases, such as `"person as p"` | Runtime only |
| CTEs and aggregates | Not part of the complete typed string API yet |
| Selected aliases in `order_by` | The 8 most recent selected fields |
| `select_from(table)` with `table: str` | Rejected by the generated interface |
| PyCharm | Not verified |

For dynamic table names, use `Pysely(schema=DatabaseSchema, dialect=dialect)`.
That runtime-only path returns dictionary rows without schema-specific static checks.

### Dynamic aliases

Prefer `select_as("id", "person_id")` over an alias computed at runtime.

- Pyright falls back to `object` values for a plain `str` alias.
- mypy does not enforce `LiteralString` here and can infer keys too broadly.
- A union alias such as `Literal["a", "b"]` exposes both keys statically,
  although only one exists at runtime.

These are known limitations, not guarantees of full safety for dynamic aliases.

### Editor messages and suggestions

Enum suggestions may include values from unrelated columns. Invalid values still
produce type errors in both checkers.

An invalid call can produce an error on the whole query chain as well as the
argument. Pyright's `strict` mode may add “unknown type” errors on later calls.

The playground uses Pyright `standard` mode. Choose the same mode in Pylance
for comparable diagnostics; Pysely does not filter them.

## Advanced: query helpers

Generated query class names exist only in the stub. Use postponed annotations
and import these names under `TYPE_CHECKING`.

```python
from __future__ import annotations

from typing import TYPE_CHECKING, TypeVarTuple

if TYPE_CHECKING:
    from dbschema import PersonQuery

FieldsT = TypeVarTuple("FieldsT")


def first_ten(query: PersonQuery[*FieldsT]) -> PersonQuery[*FieldsT]:
    return query.limit(10)
```

The field pack preserves the caller's selected keys and types.
Do not instantiate generated query classes or use them with `isinstance`.

## Performance

The stub can still be large. That costs editor and type-checker time, not runtime imports.

Local measurements from September 12, 2026: 20 tables, 333 columns, five edit rounds.

| Measurement | Result |
| --- | --- |
| Stub size | 557,334 bytes; 581,860 before this optimization pass |
| Generation time | 1.55 seconds |
| Median single-table select completion | 75 ms |
| Median select completion, two / three tables | 593 / 962 ms |
| Cold Pyright / mypy checks | 3.60 / 45.12 seconds |
| Warm mypy check | 0.24 seconds |

These are local results, not latency guarantees. Exact `select` still needs
column-specific overloads and remains the main scaling bottleneck.

Shared predicate generics reduce duplication. Flat field packs replace nested
result types. Already-nullable columns now avoid redundant overloads, and the
generator emits stub signatures directly. Exact projections still need per-column work.

Reproduce the benchmark:

```bash
uv run python scripts/benchmark_typing.py --tables 20 --rounds 5
```

See [the design decision](adr/0007-type-only-typgen.md) for implementation details.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Queries](queries.md){ .md-button }
[Type generation →](typgen.md){ .md-button .md-button--primary }

</nav>
