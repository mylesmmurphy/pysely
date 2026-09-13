# Roadmap

This is a direction, not a release schedule.
See [Project status](project-status.md) for what works today.

## 1. Foundations — implemented

- Immutable query builders and SQL compilation.
- Driver bindings and bound parameters.
- Packaging, linting, and type-checker CI.

## 2. Database execution — implemented, expanding

PostgreSQL (`asyncpg`), MySQL (`asyncmy`), and SQLite (`aiosqlite`) support
async execution, transactions, and connection cleanup.

Additional driver targets:

- Psycopg 3 and `psycopg_pool`.
- aiomysql, including MariaDB use cases.

## 3. SQL and typing — in progress

- Extend CTE, aggregate, and DDL support.
- Add schema builders for tables, columns, indexes, and constraints.
- Add schema-specific typing for string-based writes.
- Reduce exact `select` overhead on large schemas.

Keep the existing chained query API and stock mypy/Pyright support.
Type generation stays in adjacent `.pyi` files, not runtime modules.

## 4. Database lifecycle — in progress

Introspection already scaffolds Python schemas for PostgreSQL, MySQL, and SQLite.

Still planned:

- Ordered `up` and `down` migrations.
- Migration history, locking, and rollback.
- Dialect-aware transactions for schema changes.

`typgen --check` only checks stub freshness. It is not a database migration
or live-schema drift check.

## 5. Release hardening — ongoing

- Test cancellation, streaming, and failure cleanup.
- Expand SQL behavior coverage against the Kysely parity ledger.
- Measure runtime costs and editor latency.
- Verify supported drivers, Python versions, and packaging.

Existing CI tests are a foundation, not the final release gate.

## Editor commitments

- Use ordinary Python types with no required checker plugin.
- Test stock Pyright completion and both checkers' diagnostics.
- Keep playground diagnostics unchanged.
- Verify VS Code/Pylance and PyCharm behavior before claiming support.

A browser-only workaround must not hide a limitation users will encounter locally.

## Later database targets

Add SQL Server and PGlite runtime adapters after the primary databases meet
the production-readiness requirements.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Project status](project-status.md){ .md-button }
[Open playground editor ↗](playground.md){ .md-button .md-button--primary }

</nav>
