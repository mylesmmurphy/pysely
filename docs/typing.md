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
| Unknown, unjoined or ambiguous columns in `select`, `select_as`, `where`, `where_ref`, joins and callbacks | Error |
| `where` values checked per operator family (see below) | Verified |
| Result rows: `row["id"]` is `int`, `row["kind"]` is the enum, unknown keys are errors | Verified |
| `select_as` alias typed as a key | Verified for a literal alias |
| Left join: the joined table's keys become `X \| None` | Verified |
| Right and full join: every key becomes `X \| None` | Verified (conservative) |
| `.select([...])` lists | Scope-checked; keys read as `object` |
| Typed string writes | Not yet |
| Table aliases (`"person as p"`) | Runtime only |
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

Typed queries return `DatabaseRow` instances: immutable mappings with
per-key value types. `dict(row)` and `**row` do not type-check because the
row rejects unknown keys statically; use `row.to_dict()`. Selecting the same
output name twice is a runtime error (`select_as` to disambiguate).

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
- **Helpers** must name the scope they need
  (`DatabaseQuery[PersonColumns, NullT, RowT]`); `ColumnT | PersonColumns`
  parameters are solved inconsistently by the two checkers.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Queries](queries.md){ .md-button }
[Code generation →](codegen.md){ .md-button .md-button--primary }

</nav>
