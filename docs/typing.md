# Schema and typing

Pysely works with ordinary Python tooling. No checker plugin is required.

- Annotated schemas provide runtime name validation.
- Schema-specific interfaces provide completions and static checks.
- VS Code with Pylance is the primary editor target.

Runtime schemas use annotated classes:

```python
class PersonTable:
    id: int
    first_name: str


class Database:
    person: PersonTable


db = Pysely(schema=Database, dialect=PostgresDialect(pool=pool))
rows = await db.select_from("person").select(["id", "first_name"]).execute()
```

This form validates names at runtime. Its portable result type is the conservative
`dict[str, object]`.

## Schema-specific interfaces

Schema-specific interfaces provide:

- Table and in-scope column completion.
- Static rejection of invalid table and column names.
- Execution through the standard Pysely runtime.

Database introspection and the `pysely codegen` command are not implemented. Until
they ship, defining a schema-specific interface is a manual step.

| Capability | Status |
| --- | --- |
| Table-name completion | Available in schema-specific interfaces |
| Columns before and after inner joins | Available in schema-specific interfaces |
| Invalid and unjoined columns | Rejected in schema-specific interfaces |
| Runtime schema validation | Available |
| Column-specific comparison values | Available through the optional mypy plugin |
| Typed string writes | Not implemented |
| Narrow `.select()` results | Single literal columns retain result keys; lists and tuples use conservative types |
| `.select_as(source, alias)` | Direct literal aliases retain key and value types |
| Dynamic or duplicate aliases | Conservative key/value types |
| Outer-join nullability | Not yet implemented |
| PyCharm support | Not documented |

Chained `.select_as()` calls retain literal result keys without a fixed projection
limit. Different value types, duplicate aliases, and dynamic aliases use a safe,
broader mapping type.

## Editor diagnostics

Language servers may underline a larger fluent chain when a call fails, because
the chain is the call's receiver. Failed overloads and missing arguments can also
produce follow-on unknown-type errors. Ordinary invalid `where` and `select`
columns receive argument-sized diagnostics.

Fluent chaining is the intended API. The playground forwards language-server
diagnostics and does not add execution errors as editor markers.

For a temporarily tighter diagnostic range, the same builder can be written as
separate calls while locating an error:

```python
query = db.select_from("person")
joined = query.inner_join("pet", "owner_id", "person.id")
filtered = joined.where("first_name", "=", "Jennifer")
selected = filtered.select("first_name")
result = selected.select_as("pet.name", "pet_name")
```

Each variable keeps a distinct name because joins and projections change the
query's static type. Fluent chaining is the normal Pysely style; use this form
only when a checker attaches a call-level error to a larger chain.

## Optional mypy checks

The mypy plugin is optional:

```toml
[tool.mypy]
plugins = ["pysely.mypy"]
```

It checks literal table and column names, comparison values, write keys, and some
projected result shapes. It is optional and has no runtime dependency.

## Syntax differences from Kysely

Pysely prefers `.select_as("pet.name", "pet_name")` for portable typed aliases.
Python typing cannot split an arbitrary `"pet.name as pet_name"` string into a
source type and result key.

- Direct literal aliases retain key completion and value information.
- Dynamic or conflicting aliases use conservative result types.
- The single-string form compiles at runtime without the same static inference.

Results are dictionaries: use `row["first_name"]` for field access and key
completion. Dot access such as `row.first_name` is not supported. When selected
columns have different value types, the dictionary value type is their union.

The browser [playground](playground.md) runs Pysely for query compilation and
Pyright for editor intelligence.
