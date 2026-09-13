# 0007: Handwritten schemas with adjacent type stubs

Supersedes ADR 0006's generated runtime modules and nested rows.

The only schema-specific generated file is `.pyi`. `SchemaDefinition.connect()`
binds a handwritten schema to a dialect and creates the shared `SchemaClient`.
All query execution uses shared `FlatQuery`/`QueryCore` implementations. The
generated client/query classes describe those objects; they do not exist at
runtime and must only be imported under `TYPE_CHECKING` when used in annotations.

Predicate and callback overloads are generated once per schema value family.
Queries carry scoped column unions as generic arguments. Exact string `select`
and table-grouped `select_as` retain their previous mapping/nullability rules.
Selected fields form a flat `TypeVarTuple`, with a shared 64-position row stub.

Scope checking lives in a separate `_QueryScope` base. Combining scope-dependent
explicit receivers and variadic fields in one receiver caused incorrect mypy
nullability inference. The non-variadic scope base lets both checkers validate
membership while retaining the query's class-level field pack. No checker-specific
branches, plugins, or configuration are required.

Limits: exact `select` still generates per-column overloads and remains the
large-schema bottleneck. Enum completion lists can include unrelated values;
both checkers still reject invalid arguments. Right/full-join nullability remains
conservative; list projections and dynamic aliases retain their existing limits.

The fixed-scope TOML prototype and generated-runtime path were removed, not kept
as compatibility modes. Generated stubs use compact formatting independent of
developer formatter versions; their public signatures are checked directly.
