# Schema and typing

Use one annotated class per table and one class mapping database table names to
those classes. No constructors or `Column` objects are needed for string queries.

```python
class PersonTable:
    id: int
    first_name: str


class Database:
    person: PersonTable


db = Pysely(schema=Database, dialect=PostgresDialect(pool=pool))
rows = await db.select_from("person").select(["id", "first_name"]).execute()
```

The database class supplies runtime schema information and the generic database
type. Schema information is preserved in transactions and connection scopes.
`TypedDict` table definitions are also supported.

## Mypy

Enable the optional plugin in your project's `pyproject.toml`:

```toml
[tool.mypy]
plugins = ["pysely.mypy"]
```

For literal string queries the plugin checks table and column names, tracks inner
joins and table aliases, validates comparison values and write keys, and infers a
`TypedDict` result containing selected fields and insert/update returning fields.
Without the plugin, results use the conservative `dict[str, object]` type.

The plugin adds mypy diagnostics and inference. It does not install completion
support into Pylance or other Python language servers. The playground provides its
own schema-aware table and column suggestions through Monaco.

External-editor completion is deferred until the core query, schema, migration,
and code-generation surfaces are stable. See the [roadmap](ROADMAP.md).

The initial string query surface covers reads, inner joins, predicates,
projections, inserts, updates, deletes, and returning projections. The earlier
object-based builders remain available for compatibility.
