# Implementation roadmap

## Stage 1: Foundations

- Package, CI, parity ledger, and decision records.
- Immutable AST, visitor/transformer, catalog types, and generated fixture.
- Offline select compilation and portable typing checks.

Exit: package builds, AST branches remain independent, compiler tests pass for all
binding profiles, and the generated fixture passes mypy and Pyright.

## Stage 2: Execution

- Driver and connection protocols, plugin pipeline, result types, and SQLite driver.
- Async execution, resource providers, transactions, savepoints, and cleanup.
- PostgreSQL and MySQL adapters with live CI wiring.

Exit: parameterized queries and transaction failure paths pass against PostgreSQL,
MySQL, and SQLite.

## Stage 3: SQL surface

- Complete read and write builders, expressions, joins, CTEs, set operations, and DDL.
- Add Kysely-style schema builders for creating, altering, and dropping tables,
  columns, indexes, constraints, and schemas where the dialect supports them.
- Capability checks and dialect helpers.
- Enhanced mypy inference for scope, projection, aliases, and null-extending joins.

Exit: every applicable upstream behavior has runtime, compiler, and typing evidence.

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

Exit: all release acceptance criteria in the architecture handoff are evidenced.

## Deferred editor integration

- Build external-editor completion on shared schema/query analysis without changing
  the public query API.
- Add VS Code extension-host end-to-end tests for string completion, invalid table
  and column diagnostics, comparison value types, and inferred result types.
- Keep the completion protocol editor-neutral so other editors can integrate with
  the same analysis after the VS Code/Pylance path is proven.

This work remains deferred until the core query, schema, migration, and codegen
surfaces are stable.

## Post-readiness dialect expansion

- Add MSSQL and PGlite runtime adapters after the PostgreSQL, MySQL, and SQLite
  production gates are complete.
