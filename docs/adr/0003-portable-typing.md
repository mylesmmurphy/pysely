# ADR 0003: Portable and enhanced typing

Status: superseded by [ADR 0007](0007-type-only-typgen.md), via
[ADR 0006](0006-generated-typed-interfaces.md).

## Original direction

Use literal types, overloads, and generic query scope for table and column
completion in ordinary Python editors.

Keep the runtime schema-independent. Avoid broad `str` overloads that would
silently accept misspelled columns.

## What changed

- The optional mypy plugin was removed.
- Generated runtime clients were replaced by adjacent `.pyi` stubs.
- `pysely typgen` now serves mypy and Pyright from one interface.

## Principle retained

The playground uses real Python compilation and stock Pyright.
Do not mock completion or filter diagnostics to hide typing limitations.
