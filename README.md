# Pysely

Pysely is an async-first, typed Python SQL query builder inspired by Kysely.

The project is in active development. The current implementation supports immutable
typed table metadata, select construction, predicates, aliases, and offline SQL
compilation for PostgreSQL, MySQL, SQLite, SQL Server, and PGlite binding profiles.
SQLite also supports async execution and transaction scopes through `aiosqlite`.
Insert, update, and delete builders support bound values and returning projections.

```python
query = (
    db.select_from(users)
    .select(users.c.id, users.c.email)
    .where(users.c.email.eq("myles@example.com"))
)

compiled = query.compile()
```

Install SQLite execution support with `pysely[sqlite]`.

See `docs/ROADMAP.md` for implementation stages and current acceptance targets.
