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

Annotated schema classes validate table and column names at runtime. For static
checking in mypy and Pyright, generate a typed interface from the same classes:

```bash
pysely codegen schema.py --output db.py
```

Python has no `keyof` or mapped types, so the literal column names have to exist
in real annotations for a checker to see them. Generation writes them once and
serves both checkers; no checker plugin is required. See
[Code generation](https://pysely.dev/codegen/).

Install the development release with the driver extra for your database:

```bash
pip install --pre "pysely[postgres]"
```

The available extras are `postgres`, `mysql`, and `sqlite`.

See `docs/ROADMAP.md` for implementation stages and current acceptance targets.
