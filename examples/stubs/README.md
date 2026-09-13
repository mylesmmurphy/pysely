# Handwritten runtime, generated types

- `dbschema.py`: tables plus `DatabaseSchema(SchemaDefinition)`.
- `dbschema.pyi`: generated interface; never imported by Python.
- `db.py`: a configured SQLite client (opened lazily).
- `queries.py`: ordinary chained queries with checked result types.

From the repository root:

```sh
uv run pysely typgen examples/stubs/dbschema.py
uv run pysely typgen examples/stubs/dbschema.py --check
uv run pyright examples/stubs
uv run mypy --strict examples/stubs/queries.py
```

The query example expects your database tables to exist. Schema generation does
not create or migrate database tables. Joins and projections are written in
Python, never declared in a typgen configuration.
