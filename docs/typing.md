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
| Narrow `.select()` results | Conservative; selected names remain scope-checked |
| `.select_as(source, alias)` | Verified with stock Pyright and mypy for direct literal aliases |
| Dynamic or duplicate aliases | Conservative key/value types |
| Outer-join nullability | Not yet implemented |
| PyCharm behavior | Unverified |

Chained `.select_as()` calls accumulate literal result keys without a fixed
projection-count limit. When aliases select different value types, the mapping's
value type widens to their safe union. Duplicate aliases do the same. A dynamic
alias cannot provide a finite key completion set and therefore falls back to a
broader mapping type.

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
