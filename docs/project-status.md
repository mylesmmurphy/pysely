# Project status

Pysely is under active development and is not production-ready.

## Implemented

- Immutable query nodes and builders
- PostgreSQL, MySQL, and SQLite compilation and async execution
- Select, insert, update, and delete
- Bound predicates, aliases, returning projections, and result metadata
- Transactions and single-connection scopes
- Ordered query and result plugins
- Ruff, mypy, Pyright, package, and live database CI gates

## In progress

- Ordering, limits, joins, and the broader Kysely SQL surface
- Stronger projected-row inference
- Failure-path, cancellation, and lifecycle hardening
- Schema introspection, generation, migrations, and streaming

MSSQL and PGlite runtime adapters are post-readiness work.

See the [implementation roadmap](ROADMAP.md) for staged acceptance targets.
