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

Write your tables as annotated classes, generate one module, import it:

```bash
pysely codegen tables.py --output schema.py
```

```python
from schema import schema
from pysely import Database

db = Database(schema=schema, dialect=dialect)
```

mypy and Pyright now know every table, column, and value type. No checker
plugin. See [Code generation](https://pysely.dev/codegen/).

Install the development release with the driver extra for your database:

```bash
pip install --pre "pysely[postgres]"
```

The available extras are `postgres`, `mysql`, and `sqlite`.

See `docs/ROADMAP.md` for implementation stages and current acceptance targets.
