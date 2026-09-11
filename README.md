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
    .select("id")
    .select("first_name")
    .where("first_name", "=", "Jennifer")
)

compiled = query.compile()
```

Define your tables as annotated classes, then generate one self-contained
module that gives mypy and Pyright every table, column, and value type:

```bash
pysely codegen schema.py --output db.py
```

Import `Database` from `db.py` and nothing else. Python has no `keyof` or
mapped types, so the literal column names have to exist in real annotations for
a checker to see them; generation writes them once and serves both checkers with
no plugin. See [Code generation](https://pysely.dev/codegen/).

Install the development release with the driver extra for your database:

```bash
pip install --pre "pysely[postgres]"
```

The available extras are `postgres`, `mysql`, and `sqlite`.

See `docs/ROADMAP.md` for implementation stages and current acceptance targets.
