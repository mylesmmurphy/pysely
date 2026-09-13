# Project status

Pysely is pre-alpha and **not production-ready**. APIs may change.

## Available now

| Area | Implemented |
| --- | --- |
| Databases | Async PostgreSQL, MySQL, and SQLite execution |
| Reads | Select, filters, joins, aliases, ordering, paging, grouping, set operations |
| Writes | Insert, update, delete, and supported returning clauses |
| Connections | Transactions, single-connection scopes, and cleanup |
| Typing | mypy/Pyright checks from adjacent `.pyi` stubs |
| Tooling | Schema introspection and an interactive browser playground |

`typgen` generates no runtime module. SQL execution uses shared library code.

## Know the boundaries

- String-based writes do not yet have schema-specific static checking.
- Exact result types have limits for wide rows, lists, and dynamic aliases.
- CTEs, aggregates, and DDL are not a complete typed SQL surface.
- SQL Server and PGlite currently support offline compilation, not execution.

See [Schema and typing](typing.md#current-limits) for precise typing boundaries.

## Before a production release

- Complete the supported SQL and migration APIs.
- Harden cancellation, failures, and resource cleanup.
- Improve large-schema type-checking and completion speed.
- Expand parity, runtime, and editor verification.

CI already covers Ruff, mypy, Pyright, packaging, live databases, and browser tests.
Passing those checks is not a production-readiness claim.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Dialects](dialects.md){ .md-button }
[Roadmap →](ROADMAP.md){ .md-button .md-button--primary }

</nav>
