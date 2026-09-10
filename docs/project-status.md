# Project status

Pysely is under active development and is not production-ready.

## Implemented

- Immutable query nodes and builders
- Annotated database schemas and string-based reads and writes
- Optional mypy plugin for literal string queries, scope checks, and projected rows
- Schema-specific typing foundation for standard Python editors
- Three-pane playground with Pysely compilation and Pyright language intelligence
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

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Dialects](dialects.md){ .md-button }
[Roadmap →](ROADMAP.md){ .md-button .md-button--primary }

</nav>
