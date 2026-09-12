# Schema and typing

Two layers, one source of truth:

| Layer | Source | What it does |
| --- | --- | --- |
| Runtime | your table classes | validates table and column names when a query is built |
| Static | `schema.py`, generated from those classes | lets mypy and Pyright check queries and complete names |

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
pysely codegen tables.py --output schema.py
```

```python
from schema import schema
from pysely import Database

db = Database(schema=schema, dialect=dialect)
```

Each line below is covered by a test that runs stock mypy 1.20 and Pyright
1.1.413 against a freshly generated module (`test/typings`).

| Capability | Status |
| --- | --- |
| Table and column completion, in scope only | Verified |
| Unknown, unjoined or ambiguous columns in `select`, `select_as`, `where`, `where_ref`, `group_by`, `having`, `order_by`, joins and callbacks | Error |
| `where` values checked per operator family (see below); `having` takes the callback form | Verified |
| Result rows: `row["id"]` is `int`, `row["kind"]` is the enum, unknown keys are errors | Verified for the first 16 fields |
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

Typed queries return `pysely.Row` instances: immutable mappings whose static
type lists the selected fields newest first
(`Row[Cons[Literal["id"], int, Cons[Literal["name"], str, Nil]], Never]`).
Lookups are typed for the 16 most recent fields; beyond that a key reads as
`object`. `dict(row)` and `**row` do not type-check because the row rejects
unknown keys statically; use `row.to_dict()`. Selecting the same output name
twice is a runtime error (`select_as` to disambiguate); statically the newer
field wins.

## Query classes

`select_from("person")` returns `PersonQuery`, which only carries that table's
overloads, so single-table completions stay fast however large the schema.
Any join returns `DatabaseQuery`, which carries every table's overloads; its
completion latency grows with the total column count (see
[Performance](#performance)).

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
- **Helpers** take the concrete query class (`PersonQuery[FieldsT]`) or name
  the joined tables (`DatabaseQuery[Literal["person", "pet"], PersonScope |
  PetScope, NullT, FieldsT, StarT]`); `ColumnT | PersonColumns`-style
  parameters are solved inconsistently by the two checkers.
- **mypy time** grows with row depth: a lookup on a row with 16 fields takes
  about two seconds in mypy 1.20. Pyright is unaffected.

## Performance

Measured with `scripts/benchmark_typing.py` on synthetic schemas (10-30
columns per table, six shared column names); full table in
[ADR 0006](adr/0006-generated-typed-interfaces.md). In short: Pyright
re-evaluates every reachable class on each edit, so completion latency grows
with the generated module. Single-table completions stay under 300 ms up to
about 20 tables and reach 1.5 s at 60; joined-query completions are 1.9 s at
20 tables. Pyright refuses modules past roughly 80 tables; split larger
databases into several database classes.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Queries](queries.md){ .md-button }
[Code generation →](codegen.md){ .md-button .md-button--primary }

</nav>
