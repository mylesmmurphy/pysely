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

For literal string read queries the plugin checks table and column names, tracks
inner joins and table aliases, validates comparison values, and infers a
`TypedDict` result containing the selected fields, including selection aliases.
Without the plugin, results use the conservative `dict[str, object]` type.

The plugin adds mypy diagnostics and inference. It does not install completion
support into Pylance or other Python language servers. The playground provides its
own schema-aware table and column suggestions through Monaco. General Python
language-server features and generated editor stubs are not implemented yet.

VS Code/Pylance is the first external editor target. Cross-editor support should
reuse schema/query analysis rather than change the public API. Standard type
stubs can expose literal names; scope-sensitive completion across joins and
aliases needs additional editor tooling. Support in every editor is not yet
claimed.

The initial string query surface covers reads, inner joins, predicates, and
projections. The existing object-based write builders remain available while
write schema metadata and string writes are brought into this model.
