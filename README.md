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

Write tables and `DatabaseSchema(SchemaDefinition)` in `dbschema.py`, then generate
its adjacent type stub:

```bash
pysely typgen dbschema.py
```

```python
from dbschema import DatabaseSchema

db = DatabaseSchema.connect(dialect=dialect)
```

Python runs your handwritten schema and Pysely's shared runtime; mypy and
Pyright read `dbschema.pyi`. **Only type stubs are generated—no massive generated
runtime file.** Python never imports the stub, and it can be left out of runtime
deployments. No checker plugin. See [Type generation](https://pysely.dev/typgen/).

The docs track `main`, including the new `typgen` command. Install the current
source with the driver extra for your database:

```bash
pip install "pysely[postgres] @ git+https://github.com/mylesmmurphy/pysely.git@main"
```

The available extras are `postgres`, `mysql`, and `sqlite`.

See `docs/ROADMAP.md` for implementation stages and current acceptance targets.

See [examples/stubs](examples/stubs/README.md) for the three-file setup.
