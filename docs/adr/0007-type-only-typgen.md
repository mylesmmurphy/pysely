# ADR 0007: Handwritten schemas and type stubs

Status: accepted. Supersedes [ADR 0006](0006-generated-typed-interfaces.md).

## Decision

Generate only adjacent `.pyi` stubs with `pysely typgen`.
Do not generate schema-specific runtime implementations.

`SchemaDefinition.connect()` binds the handwritten schema to a dialect.
Shared `SchemaClient`, `FlatQuery`, and `QueryCore` code handles execution.

Generated client and query names describe those runtime objects.
They exist only in stubs; annotation imports require `TYPE_CHECKING`.

## Type representation

- Predicates and callbacks share overloads by schema value type.
- Generic column unions track which columns are available.
- `select` preserves the selected key and value type.
- `select_as` groups columns by value type and tracks the alias.
- A flat `TypeVarTuple` stores result fields; the row stub supports 64 lookup positions.

## Why a separate scope base?

Putting scope checks and variadic result fields in one explicit receiver caused
incorrect mypy nullability inference.

The non-variadic `_QueryScope` base checks table membership.
The query's field pack retains the selected result types.

Both checkers use the same declarations. No checker-specific branches or plugins are required.

## Remaining limits

- Exact `select` overloads remain the large-schema bottleneck.
- Enum completion may suggest unrelated values; invalid arguments still fail.
- Right/full joins use conservative nullability.
- Lists and dynamic aliases retain their documented typing limits.

See [Schema and typing](../typing.md) for user-facing details.

## Removed approaches

The fixed-scope TOML prototype and generated-runtime path were removed.
They are not compatibility modes.

Stubs use deterministic compact formatting. Tests check their public signatures directly.

## Generator optimization follow-up

Already-nullable columns use one projection overload, preserving the existing
join state. Required columns retain separate normal and outer-join forms.

The renderer emits final stub signatures directly. It no longer builds runtime
wrappers or nested field types just to transform and discard them.

Cross-table signature merging failed scope or inference checks in the tested
prototypes. State aliases reduced bytes but slowed joined completions; neither was kept.
