# Pysely

Pysely is an async-first, typed Python SQL query builder inspired by Kysely.

Documentation: [pysely.dev](https://pysely.dev)

The project is in active development. The current implementation supports immutable
typed table metadata, select construction, predicates, aliases, and offline SQL
compilation for PostgreSQL, MySQL, SQLite, SQL Server, and PGlite binding profiles.
SQLite also supports async execution and transaction scopes through `aiosqlite`.
Insert, update, and delete builders support bound values and returning projections.

```python
query = (
    db.select_from("person")
    .select(["id", "first_name"])
    .where("first_name", "=", "Jennifer")
)

compiled = query.compile()
```

Install driver support with `pysely[postgres]`, `pysely[mysql]`, or
`pysely[sqlite]`.

See `docs/ROADMAP.md` for implementation stages and current acceptance targets.
