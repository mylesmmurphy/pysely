# Schema and typing

Pysely's baseline typing target is ordinary Python tooling: generated schema
interfaces, standard annotations, and no required checker plugin. VS Code with
Pylance is the primary target; PyCharm remains unverified.

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

This form validates names at runtime. Until schema code generation ships, its
portable result type remains the conservative `dict[str, object]`.

## Generated interfaces

The generated client design now uses `Literal` names, overloads, and generic query
scope. A permanent fixture verifies that standard Pyright can suggest tables,
suggest only columns currently in scope, add columns after a join, and reject
out-of-scope names. The same query still executes through the normal Pysely runtime.

Database introspection and the `pysely codegen` command are not implemented yet.
They are the next step needed to make this generated interface the normal workflow.

| Capability | Portable status |
| --- | --- |
| Table-name completion | Verified with Pyright language server 1.1.413 |
| Columns before and after inner joins | Verified with Pyright language server 1.1.413 |
| Invalid and unjoined columns | Verified with Pyright 1.1.413 |
| Runtime schema validation | Verified |
| Column-specific comparison values | Limited to the optional mypy plugin |
| Typed string writes | Planned for generated interfaces |
| Exact narrow projection results | Limited to the optional mypy plugin |
| Aliases and outer-join nullability | Not yet implemented |
| PyCharm behavior | Unverified |

## Optional mypy checks

The existing plugin remains an optional enhancement:

```toml
[tool.mypy]
plugins = ["pysely.mypy"]
```

It checks literal table and column names, comparison values, write keys, and some
projected result shapes. It is not required by Pysely at runtime and is no longer
the foundation of the default typing design.

The browser [playground](playground.md) runs the real Pysely package for query
compilation. It does not invent completion results that a standard editor may not
provide.
