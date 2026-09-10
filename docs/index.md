# Typed SQL for Python

Pysely is an async-first SQL query builder inspired by
[Kysely](https://kysely.dev). It combines immutable queries, explicit database
types, and parameterized SQL without hiding the SQL you write.

!!! warning "Early development"

    Pysely is not production-ready. The API can change while the core query
    surface is completed.

```python
rows = await (
    db.select_from("person")
    .select(["id", "first_name"])
    .where("first_name", "=", "Jennifer")
    .execute()
)
```

## Current database support

| Database | Compiler | Async execution |
| --- | --- | --- |
| PostgreSQL | Yes | `asyncpg` |
| MySQL | Yes | `asyncmy` |
| SQLite | Yes | `aiosqlite` |

MSSQL and PGlite runtime adapters are deferred until the primary dialects meet
the production-readiness gates.

[Get started](getting-started.md){ .md-button .md-button--primary }
[Open interactive editor](playground.md){ .md-button }
[View on GitHub](https://github.com/mylesmmurphy/pysely){ .md-button }
