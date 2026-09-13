# Schema and typing

Two layers, one source of truth:

| Layer | Source | What it does |
| --- | --- | --- |
| Runtime | your table classes | validates table and column names when a query is built |
| Static | `schema.pyi`, generated beside the handwritten schema | lets mypy and Pyright check queries and complete names |

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

Define your schema with `SchemaDefinition` as shown in [type generation](typgen.md),
generate its stub, and import the handwritten schema normally:

```bash
pysely typgen schema.py
```

```python
from schema import DatabaseSchema

db = DatabaseSchema.connect(dialect=dialect)
```

Each line below is covered by a test that runs stock mypy 1.20 and Pyright
1.1.413 against a freshly generated module (`test/typings`).

| Capability | Status |
| --- | --- |
| Table and column completion, in scope only | Verified |
| Unknown, unjoined or ambiguous columns in `select`, `select_as`, `where`, `where_ref`, `group_by`, `having`, `order_by`, joins and callbacks | Error |
| `where` values checked per operator family (see below); `having` takes the callback form | Verified |
| Result rows: `row["id"]` is `int`, `row["kind"]` is the enum, unknown keys are errors | 64-field lookup capacity; 50-field mixed projections regression-tested |
| `select_as` alias typed as a key; `order_by` accepts selected aliases | Verified for a literal alias (aliases: first 8 fields) |
| Left join: the joined table's keys become `X \| None` | Verified |
| Right and full join: every key becomes `X \| None` | Verified (conservative) |
| `union`/`union_all`/`intersect`/`except_` require the same selected shape | Verified |
| `.select([...])` lists | Scope-checked; every key of that row reads as `object` |
| Typed string writes | Not yet |
| Table aliases (`"person as p"`), CTEs | Runtime only / not yet |
| PyCharm | Not verified |

## Names

- A bare name works when only one table in the database declares it, or when
  it is the only table in the query (`db.select_from("person").select("id")`).
- After a join, a name two tables declare must be qualified: `person.id`.
  The static rule is stricter than the runtime one in one case: a joined
  query with a bare name that is unique in the *query* but not in the
  database must still qualify it.
- `.select_as("pet.name", "pet_name")` keeps the alias typed; the string form
  `"pet.name as pet_name"` is runtime only.

## Operator families

| Operators | Value |
| --- | --- |
| `=` `!=` `<>` `<` `<=` `>` `>=` | the column's type, without `None` |
| `is` `is not` | `None` |
| `like` `not like` | `str`, string columns only |
| `in` `not in` | `list` or `tuple` of the column's type |

The same rules apply inside `where(lambda eb: ...)`; `eb.and_`, `eb.or_`,
`eb.not_` and `eb.ref` compose them.

## Rows

Typed queries return `pysely.FlatRow`: immutable mappings with a flat pack of
`Field[key, value]` types, newest first. There is no nested cons-list limit.
The shared row stub provides exact lookup for the 64 most recent selections;
older keys must be accessed through `to_dict()` (they are not silently `Any`).
`get()` permits unknown keys, as ordinary mappings do. Duplicate aliases use
the latest field type; runtime duplicate-output validation remains unchanged.

## Query classes

`select_from("person")` returns `PersonQuery`, which only carries that table's
overloads, so single-table completions stay fast however large the schema.
Predicates and callbacks share generic value-family signatures. Any join returns
`DatabaseQuery`; exact `select` still carries per-column overloads, so its
completion latency grows with the total column count (see
[Performance](#performance)).

Enum value completions can include values from other schema columns, even on
single-table queries. Invalid values still produce mypy/Pyright errors.

## Known boundaries

Each has a reproducer in `test/typings`.

- **Whole-chain diagnostic.** Every typed method is an overload set, and both
  checkers report "No overloads match" on the full call expression. Pyright
  adds the argument-level error beside it. Pyright's `strict` mode also
  cascades "type of X is unknown" errors down the chain; the playground uses
  `standard`, which does not. Pick `standard` in Pylance to match.
- **Value suggestions after a join are a superset.** Pyright unions the value
  literals of every overload whose receiver matches, so an editor may offer
  `pet` enum values at a `person` column. Wrong values are still errors.
- **Non-literal aliases.** Under Pyright a `str` alias makes the row's keys
  read as `object`. mypy has no `LiteralString`, so it treats a `str` alias as
  a literal and types every key as that column. A union alias
  (`Literal["a", "b"]`) types both keys under both checkers although only one
  exists.
- **List projections** keep scope checks but cannot capture keys: mypy infers
  `list[str]` for a list literal.
- **Dynamic table names** (`select_from(table)` with `table: str`) are a
  static error; use the untyped `Pysely` client for those.
- **Helpers** can preserve the flat pack using `TypeVarTuple` and
  `PersonQuery[*FieldsT]`. Generated query class names are type-only: import
  them under `TYPE_CHECKING` and use postponed annotations.
- **Wide rows** have exact lookup capacity for 64 selections. The regression
  suite checks every key and type in a mixed 50-column projection.

## Performance

The stub backend still has a real bottleneck: exact `select` overloads.
On the representative 20-table/333-column schema, the September 12 local run
produced a 582,755-byte stub (previous output was about 1.3 MB). Three edit rounds
gave median select completion times of 106 ms single-table, 715 ms with two
tables, and 1,070 ms with three. Cold checks across the benchmark's query/projection
fixtures took 6.16 s in Pyright and 53.18 s in mypy; warm mypy took 0.26 s.
These are local measurements, not latency guarantees.

Predicates now share one overload family per schema value type. Result fields
are flat rather than recursively nested. Neither change eliminates the
per-column exact projection work; optimizing that remains separate.
Reproduce with `uv run python scripts/benchmark_typing.py --tables 20 --rounds 3`.
Historical measurements in ADR 0006 describe the old backend.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Queries](queries.md){ .md-button }
[Type generation →](typgen.md){ .md-button .md-button--primary }

</nav>
