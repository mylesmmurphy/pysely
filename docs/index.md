# Typed SQL for Python

Write SQL-shaped queries in Python, with editor checks for column names,
filter values, and selected result types. Pysely is async-first and inspired by
[Kysely](https://kysely.dev).

!!! warning "Early development"

    Pysely is not production-ready. The API can change while the core query
    surface is completed.

```python
rows = await (
    db.select_from("person")
    .select("id")
    .select("first_name")
    .where("first_name", "=", "Jennifer")
    .execute()
)
```

## Types without generated runtime code

Write your schema in `dbschema.py`. Run `pysely typgen dbschema.py` to generate
`dbschema.pyi` for mypy and Pyright.

Python never loads the stub. Your app uses the handwritten schema and shared
library code—no massive generated runtime file and no checker plugin.

## Pick a starting point

- [Run your first query](getting-started.md) with a complete SQLite example.
- [Browse the query APIs](queries.md) for joins, filters, and transactions.
- [Understand typing](typing.md) and its current limits.
- [Try the playground](playground.md) without installing anything.

## Current database support

| Database | Compiler | Async execution |
| --- | --- | --- |
| PostgreSQL | Yes | `asyncpg` |
| MySQL | Yes | `asyncmy` |
| SQLite | Yes | `aiosqlite` |

MSSQL and PGlite runtime adapters are deferred until the primary dialects meet
the production-readiness gates.

[Get started](getting-started.md){ .md-button .md-button--primary }
[Open interactive editor ↗](playground.md){ .md-button }
[View on GitHub](https://github.com/mylesmmurphy/pysely){ .md-button }
