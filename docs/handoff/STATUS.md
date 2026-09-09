# Pysely implementation status

Baseline commit: `c54987f4d5bb1a9573c8d83e1cba7365770cc016`

Current project commit: see repository `HEAD`

Current stage: 2 - Execution

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
- Asyncpg and asyncmy pool adapters with lazy optional imports.
- Owned and borrowed PostgreSQL/MySQL pool lifecycles and transaction pinning.
- Live PostgreSQL 16.4 and MySQL 8.4 read, write, and rollback verification in CI.
- Single-connection scopes and rollback after transaction body or commit failure.
- Parenthesized boolean groups and basic column-reference comparisons.

## Implemented but unverified

- Exact projected-row inference; portable typing is intentionally conservative.

## Remaining parity gaps

- The public export and test-case inventory is in progress.
- MSSQL and PGlite runtime drivers are deferred until the primary dialects meet
  production-readiness gates.
- Joins, advanced expressions, CTEs, set operations, DDL, and other SQL surface
  features remain planned.

## Validation

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- `uv run pytest -q`: 40 passed and 2 service-dependent skips; live SQLite ran.
- PostgreSQL/MySQL live suites and required-service `--dialect` gates are wired in CI.
- GitHub Actions run `34409360952`: PostgreSQL, MySQL, and all core matrix jobs passed.
- `uv sync --locked --all-extras`: passed with asyncpg 0.31.0, asyncmy 0.2.14,
  and aiosqlite 0.22.1.
- `uv run mypy src/pysely test/fixtures/generated.py`: passed.
- `uv run mypy --strict test/typings/portable.py`: passed.
- `uv run pyright src/pysely test/typings/portable.py`: passed.
- `uv run python scripts/check_parity.py`: passed.
- `uv build --no-sources`: wheel and source distribution built successfully.
- Clean virtual environment wheel install and import: passed.

## Decisions and blockers

- See `docs/adr/`.
- No current implementation blocker. Live engine verification remains open by design.

## Next session

1. Add ordering, limits, and joins.
2. Prove the hard portable typing fixtures before starting the mypy plugin.
3. Keep MSSQL and PGlite runtime work deferred until production readiness.
