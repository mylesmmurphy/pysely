# Pysely implementation status

Baseline commit: `c54987f4d5bb1a9573c8d83e1cba7365770cc016`

Current project commit: uncommitted initial implementation

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

## Implemented but unverified

- SQLite write-builder rollback behavior; rollback and release are currently verified
  around live read execution.
- Exact projected-row inference; portable typing is intentionally conservative.

## Remaining parity gaps

- The public export and test-case inventory is in progress.
- PostgreSQL and MySQL runtime drivers are next in stage 2.
- MSSQL and PGlite runtime drivers are scheduled as stage 2 fast-follows.
- All features outside the first select compiler slice remain planned.

## Validation

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- `uv run pytest -q`: 18 passed, no skips or xfails, including live SQLite.
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

1. Add insert/update/delete builders and verify SQLite transaction rollback of writes.
2. Implement asyncpg and asyncmy pool adapters against the same driver protocol.
3. Add MSSQL, then validate a maintained PGlite Python runtime integration.
4. Add expression grouping, reference comparisons, ordering, limits, and joins.
5. Prove the hard portable typing fixtures before starting the mypy plugin.
