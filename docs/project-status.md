# Project status

Pysely is under active development and is not production-ready.

## Implemented

- Immutable query nodes and builders
- Annotated database schemas and string-based reads and writes
- Optional mypy plugin for literal string queries, scope checks, and projected rows
- Portable generated-client foundation with real Pyright language-server tests
- Three-pane Monaco playground running Pysely and upstream Pyright in browser workers
- PostgreSQL, MySQL, and SQLite compilation and async execution
- Select, insert, update, and delete
- Bound predicates, aliases, returning projections, and result metadata
- Transactions and single-connection scopes
- Ordered query and result plugins
- Ruff, mypy, Pyright, package, and live database CI gates

## In progress

- Ordering, limits, additional joins, and the broader Kysely SQL surface
- Schema-specific interface generation for standard Python editors
- Comparison, write, projection, alias, and nullability typing on generated clients
- Failure-path, cancellation, and lifecycle hardening
- Schema builders, migrations, introspection, generation, and streaming
- Browser language-server lifecycle, performance, and cross-browser test coverage

MSSQL and PGlite runtime adapters are post-readiness work.

See the [implementation roadmap](ROADMAP.md) for staged acceptance targets.
