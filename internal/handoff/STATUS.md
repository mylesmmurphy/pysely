# Pysely implementation status

Baseline commit: `c54987f4d5bb1a9573c8d83e1cba7365770cc016`

Current project commit: see repository `HEAD`

Current stage: 3 - SQL surface

## Implemented and verified

- `select.explicit_projection.where`: immutable select construction, bound values,
  aliases, explicit NULL comparisons, and identifier quoting.
- Catalog `Column` and `Table` generics, including alias rebinding without mutation.
- PostgreSQL asyncpg, MySQL asyncmy, SQLite aiosqlite, and SQL Server aioodbc
  compiler binding profiles.
- Recursive operation-node visitor and transformer coverage for the implemented AST.
- Locked build, wheel contents, `py.typed`, and isolated wheel import.
- Async SQLite execution with dictionary rows and explicit result metadata.
- Async client lifecycle and automatic commit/rollback transaction scopes.
- Duplicate projection-name rejection and closed-client enforcement.
- PGlite PostgreSQL-compatible offline compilation.
- Immutable insert, update, and delete builders with portable input typing.
- PostgreSQL/SQLite returning, MSSQL output, and unsupported-feature validation.
- Live SQLite writes with commit and rollback behavior.
- Ordered query and result plugin execution.
- Structural pool/database adapters with lazy async resource factories.
- User-provided PostgreSQL/MySQL pool lifecycles and transaction pinning.
- Live PostgreSQL 16.4 and MySQL 8.4 read, write, and rollback verification in CI.
- Single-connection scopes and rollback after transaction body or commit failure.
- Parenthesized boolean groups and basic column-reference comparisons.
- Annotated database schemas, string read queries, inner joins, and aliases.
- `pysely codegen` writes one self-contained typed module (table classes,
  `schema`, one query class per table, a generic joined-query class) from
  annotated table classes, with a `--check` drift gate in CI and a published
  pre-commit hook (ADR 0006). The `pysely.mypy` plugin was removed; generated
  source serves both checkers.
- Result rows are `pysely.Row[FieldsT, StarT]` cons lists with per-key value
  types (16 typed fields); scope-aware `select`/`select_as`/`where`/joins/
  callbacks; bare shared names accepted only while their table is alone;
  left/right/full join nullability; operator value families; order_by
  (columns and selected aliases), limit/offset, group_by, having (callback),
  union/union_all/intersect/except_.
- `pysely introspect` writes `tables.py` from SQLite, PostgreSQL or MySQL
  catalogs (types, nullability, enums, key/default comments, overrides).
- Thread-safe query compilation: a shared compiler no longer keeps bound
  parameters on the instance across concurrent calls.
- Portable generated-query wrapper and schema-specific fixture using standard
  literals, overloads, and join-scope accumulation.
- Schema-backed string inserts, updates, deletes, predicates, and returning fields.
- Monaco schema/query/SQL editors and interruptible browser compilation in a worker.
- Real Pyright language-server completion tests for table names and before/after
  inner-join column scope.

## Implemented but unverified

- Exact delete-returning inference remains unimplemented. PyCharm and Pylance
  UI behaviour are not verified (stock Pyright LSP is). PostgreSQL/MySQL
  introspection is exercised only against fixtures; SQLite is tested live.

## Remaining parity gaps

- The public export and test-case inventory is in progress.
- MSSQL and PGlite runtime drivers are deferred until the primary dialects meet
  production-readiness gates.
- CTEs, aggregates, advanced expressions, DDL, and typed string writes remain
  planned. Pyright analyses at most ~15k definitions per module (~80 tables);
  mypy needs `# mypy: ignore-errors` on the generated module.

## Validation

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- Local `pytest -q`: 55 passed and 2 service-dependent skips; live SQLite ran.
- PostgreSQL/MySQL live suites and required-service `--dialect` gates are wired in CI.
- GitHub Actions run `34409360952`: PostgreSQL, MySQL, and all core matrix jobs passed.
- `uv sync --locked --all-extras`: passed with asyncpg 0.31.0, asyncmy 0.2.14,
  and aiosqlite 0.22.1.
- `uv run mypy src/pysely test/fixtures/generated.py`: passed.
- `uv run mypy --strict test/typings/portable.py`: passed.
- `uv run pyright src/pysely test/typings/portable.py`: passed.
- Pyright 1.1.413 language-server completion tests: passed.
- `uv run python scripts/check_parity.py`: passed.
- `uv build --no-sources`: wheel and source distribution built successfully.
- Clean virtual environment wheel install and import: passed.

## Decisions and blockers

- See `docs/adr/`.
- No current implementation blocker. Live engine verification remains open by design.

## Next session

1. CTEs (runtime scope for `with_`), aggregates, and typed string writes.
2. Schema builders and migrations.
3. Verify Pylance and PyCharm UI behaviour on the generated module.
4. Keep custom editor tooling, MSSQL, and PGlite runtime work deferred.
