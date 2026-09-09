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
- Capability checks and dialect helpers.
- Enhanced mypy inference for scope, projection, aliases, and null-extending joins.

Exit: every applicable upstream behavior has runtime, compiler, and typing evidence.

## Stage 4: Lifecycle and release hardening

- Introspection, deterministic codegen, migrations, streaming, and cancellation.
- Differential tests, packaging matrix, documentation, and performance baselines.
- Close the parity ledger and production release gates.

Exit: all release acceptance criteria in the architecture handoff are evidenced.

## Post-readiness dialect expansion

- Add MSSQL and PGlite runtime adapters after the PostgreSQL, MySQL, and SQLite
  production gates are complete.
