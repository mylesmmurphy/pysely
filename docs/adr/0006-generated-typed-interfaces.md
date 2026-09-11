# ADR 0006: Generated typed interfaces

Status: accepted. Supersedes the mypy plugin in [ADR 0003](0003-portable-typing.md).

## Context

Python has no `keyof` or mapped types, so a checker can only see
`Literal["species"]` if that literal exists in a real annotation. Two ways to
produce it: a mypy plugin, or generated source. Pyright has no plugin
interface, and Pylance is the primary editor target. Pysely shipped the plugin
and a separately hand-written interface for the playground; the two could
drift with nothing enforcing agreement.

## Decision

- `pysely codegen tables.py --output schema.py` writes one self-contained
  module: the table classes, the `schema` to pass to `Database`, one query
  class per table, and a generic query class for joins. The schema class
  inherits `GeneratedSchema[DatabaseClient]`, and the `Database(schema=...)`
  factory exported from `pysely` returns that client; a plain schema gets a
  `Pysely`. A constructor cannot do this portably: mypy rejects a `__new__`
  that returns another class, and neither checker honours a metaclass
  `__call__` for it.
- The generator parses with `ast`; it never imports, executes, or connects.
- Output is committed; `--check` gates drift in CI and a pre-commit hook.
- The mypy plugin is removed.
- The heavy overloads live under `TYPE_CHECKING` beside slim runtime twins.
- The playground regenerates `schema.py` from the tables editor on every run.

### Type representation

- **Scope.** A single-table query is its own class (`PersonQuery[FieldsT]`)
  and accepts every spelling of its columns. A joined query is
  `DatabaseQuery[TablesT, ColumnT, NullT, FieldsT, StarT]`; each column
  overload matches on `self: DatabaseQuery[TablesT | Literal["pet"], ...]`, so
  only joined tables' columns are accepted. Bare names shared by two tables
  are not in `ColumnT` after a join; qualify them.
- **Rows.** `Row[FieldsT, StarT]` where `FieldsT` is a cons list of
  `(key, value)` fields, newest first. `select` prepends
  `Cons[Literal["id"], int, FieldsT]`; `select_as` prepends the alias
  `TypeVar`. `Row.__getitem__` has one overload per depth (16) and is written
  once in the library, so no row code is generated. Nullability from a left
  join is decided at `select` time (`NullT | Literal["pet"]` on the receiver);
  right and full joins set `StarT` so every lookup reads `X | None`.
- **Value shapes.** `where`/`having` overloads are grouped per (table, value
  type, operator family). Callbacks receive a generated
  `ExpressionBuilder` subclass with the same overloads.

### Rejected

- One key-group type parameter per value type (`DatabaseRow[IntKeys,
  StrKeys, ...]`): 20+ parameters per overload; 2.9 MB for 20 tables and no
  faster.
- Table tokens in the cons cell with `NullT | T` matching in `__getitem__`
  (one `select` overload per column): mypy solves `TypeVar | TypeVar` unions
  loosely and reports every key nullable.
- Generic `Field[K, V]` unions with a generic `__getitem__`: both checkers
  bind `K` to the first union member.

## Measured (2026-09-11)

macOS 14.6 x86_64, Python 3.11.4, Pyright 1.1.413, mypy 1.20.2. Synthetic
schemas: 10-30 columns per table, six column names shared by every table.
`scripts/benchmark_typing.py`.

| Tables | Columns | Generated | Overloads | Pyright warm CLI | single-table `select("` p95 | joined `select("` p95 |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | 333 | 1.2 MB | 3.1k | 3.1 s | 176 ms | 1.25 s |

Pyright's completion cost is roughly linear in the number of overloads on the
called method (about 0.4-2 ms each) and superlinear past a few thousand.
Per-table classes keep single-table queries within the 300 ms target at any
schema size; joined queries evaluate every column's overloads and scale with
the schema. That is the accepted budget; a joined-query fast path would need
one class per table pair.

## Consequences

One implementation serves both checkers. Static checking requires a generation
step; without it, runtime name validation still works. Value completion after a
join stays a superset (documented, not worked around). `pysely introspect` will
write the same module from a live database.
