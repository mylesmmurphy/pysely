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
`scripts/benchmark_typing.py --tables 20 60 --rounds 10`. The 20-table row
ran while other processes were still winding down; its generation and cold
checker times are inflated, the completion figures are not.

| Tables | Columns | Generated | Definitions | Pyright warm CLI | mypy cold / warm | `select("` p95 single-table | `select("` p95 joined (2 / 3 tables) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 333 | 1.3 MB | 3.3k | 3.1 s | 224 s* / 0.3 s | 294 ms | 1.9 s / 2.8 s |
| 60 | 1020 | 4.0 MB | 10.0k | 11.8 s | 607 s / 0.4 s | 1.47 s | 8.2 s / 9.5 s |
| 100 | 1693 | — | 17.2k | codegen refuses: over Pyright's module ceiling | | | |

\* 13.6 s on an idle machine.

What the numbers mean:

- **Pyright discards its type cache on every edit**, so each completion
  re-evaluates every class reachable from the symbols in the statement. From
  `db.select_from(...)` that is every table class plus the joined class, about
  0.1-0.15 ms per definition. The 300 ms target therefore holds up to roughly
  2,000 definitions, about 15-20 tables of 17 columns; at 60 tables a
  single-table completion takes 1.5 s. Joined-query completions add a scan of
  the joined class's `select` overloads (two per column).
- **Pyright stops analysing a module above about 15,000 definitions** (its
  code-flow complexity limit); `codegen` fails near that point.
- **mypy's overload-overlap check is quadratic** (56 s at 20 tables); the
  generated module carries `# mypy: ignore-errors`, which is the one switch
  that skips it. Cold mypy is still slow on large modules; the warm
  incremental run is fast.
- **mypy row lookups** cost about 2 s each at 16 selected fields.

Rejected mitigations: one class per joined table pair (N² classes); putting
the joined overloads on a per-table base (still evaluated per edit); table
tokens in the cons cell (mypy). The accepted budget is above; larger
databases should be split into several database classes, one module each.

## Consequences

One implementation serves both checkers. Static checking requires a generation
step; without it, runtime name validation still works. Value completion after a
join stays a superset (documented, not worked around). `pysely introspect` will
write the same module from a live database.
