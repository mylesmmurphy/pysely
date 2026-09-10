# Schema and typing

Pysely's baseline typing target is ordinary Python tooling: annotated schemas,
standard annotations, and no required checker plugin. VS Code with Pylance is the
primary target.

The current runtime schema remains simple:

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

Schema-specific interfaces use `Literal` names, overloads, and generic query scope.
They support table and in-scope column completion, reject invalid names, and execute
through the standard Pysely runtime.

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
| Narrow `.select()` results | Conservative; selected names remain scope-checked |
| `.select_as(source, alias)` | Direct literal aliases retain key and value types |
| Dynamic or duplicate aliases | Conservative key/value types |
| Outer-join nullability | Not yet implemented |
| PyCharm support | Not documented |

Chained `.select_as()` calls accumulate literal result keys without a fixed
projection-count limit. When aliases select different value types, the mapping's
value type widens to their safe union. Duplicate aliases do the same. A dynamic
alias cannot provide a finite key completion set and therefore falls back to a
broader mapping type.

## Editor diagnostics

A failed call can underline the preceding fluent chain because the checker treats
that chain as the call's receiver. This also happens for missing arguments in
non-overloaded methods. Invalid columns in ordinary `where` and `select` calls
already receive argument-sized diagnostics; failed overloads can additionally
cause unknown-type errors in later calls.

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
query's static type. Fluent chaining remains the normal Pysely style; this form is
only useful when a checker attaches a call-level error to a larger chain.

## Optional mypy checks

The existing plugin remains an optional enhancement:

```toml
[tool.mypy]
plugins = ["pysely.mypy"]
```

It checks literal table and column names, comparison values, write keys, and some
projected result shapes. It is not required by Pysely at runtime and is no longer
the foundation of the default typing design.

## Syntax differences from Kysely

Pysely prefers `.select_as("pet.name", "pet_name")` for portable typed aliases.
Kysely can infer the alias embedded in `"pet.name as pet_name"` using TypeScript's
string-literal type operations. Standard Python typing cannot perform that string
split. Keeping source and alias separate lets generated overloads preserve a direct
alias literal and map the source column to its value type. The combined string form
still compiles at runtime, but does not promise the same static inference.

The browser [playground](playground.md) runs the real Pysely package for query
compilation and upstream Pyright for editor intelligence. It does not invent
completion results that a standard editor may not provide.
