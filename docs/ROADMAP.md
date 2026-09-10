# Implementation roadmap

The playground uses the public Python types and stock language-server results.
It should match VS Code with equivalent settings. See [Project status](project-status.md)
for currently available features.

## Stage 1: Foundations

- Package and CI
- Immutable query tree and catalog types
- Select compilation and portable typing

Status: complete.

## Stage 2: Execution

- Driver and connection protocols, plugin pipeline, result types, and SQLite driver.
- Async execution, resource providers, transactions, savepoints, and cleanup.
- PostgreSQL and MySQL adapters with live CI wiring.
- Add Psycopg 3 async and `psycopg_pool` support for PostgreSQL.
- Add aiomysql support for MySQL and MariaDB.

Status: PostgreSQL with asyncpg, MySQL with asyncmy, and SQLite with aiosqlite are
complete. Psycopg 3 and aiomysql adapters are planned.

## Stage 3: SQL surface

- Complete read and write builders, expressions, joins, CTEs, set operations, and DDL.
- Add Kysely-style schema builders for creating, altering, and dropping tables,
  columns, indexes, constraints, and schemas where the dialect supports them.
- Capability checks and dialect helpers.
- Generated schema-specific clients using standard literals, overloads, and generic
  scope, with optional enhanced mypy inference kept separate.

Status: in progress.

## Stage 4: Database lifecycle

- Add a Kysely-style migrator with ordered `up` and `down` migrations, migration
  history, locking, rollback, and dialect-aware transactional behavior.
- Apply schema changes through the same schema builders used outside migrations,
  including table alterations.
- Add PostgreSQL, MySQL, and SQLite introspection.
- Generate deterministic database and table classes from an introspected schema,
  with a check mode that reports schema drift without rewriting files.

Exit: each primary dialect can be introspected, generated, migrated forward, and
rolled back against a real database.

## Stage 5: Release hardening

- Streaming, cancellation, packaging matrix, documentation, and performance
  baselines.
- Add CI end-to-end coverage against an in-memory SQLite database for query
  semantics, parameter safety, invalid-query handling, writes, and transactions.
- Port every applicable Kysely test-suite behavior to Pysely and record intentional
  Python or dialect differences in the parity ledger.
- Close the parity ledger and production release gates.

Status: planned.

## Standard editor verification

- Generate interfaces that work with Pylance, Pyright, and ordinary mypy without a
  plugin or background watcher.
- Use the stock local Pyright language server over stdio as the primary automated
  editor contract. Expand those LSP tests for invalid tables, ambiguity, values,
  writes, projections, aliases, nullable joins, helpers, and multiple schemas.
- Keep browser automation focused on a small playground integration smoke suite;
  do not duplicate the portable typing matrix in Playwright.
- Verify representative behavior in VS Code/Pylance and PyCharm manually before
  releases. A VS Code-hosted test harness is optional, not a release prerequisite.
- Keep custom LSP and editor-extension work paused unless measured portable gaps
  justify it after the core API and code generator stabilize.

Browser playground completions must come from a real language service; simulated
completion providers are not part of the product.

## Post-readiness dialect expansion

- Add MSSQL and PGlite runtime adapters after the PostgreSQL, MySQL, and SQLite
  production gates are complete.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Project status](project-status.md){ .md-button }

</nav>
