# ADR 0003: Portable and enhanced typing

Status: accepted

Schema-specific clients use ordinary `Literal` types, overloads, and generic query
scope so standard Python language servers can complete tables and currently
available columns without a Pysely editor extension.

The reusable runtime remains schema-independent. Generated clients wrap it and do
not duplicate SQL construction or execution. Strict generated entry points avoid a
blanket `str` overload because that would accept misspellings and suppress useful
literal completion.

Database introspection is not implemented. Arbitrary projection aliases and some
column-to-value relationships remain beyond the portable contract.

Superseded in part by [ADR 0006](0006-generated-typed-interfaces.md): the typed
entry points are now written by `pysely codegen`, and the optional `pysely.mypy`
plugin has been removed in favour of generated source that both checkers read.

The docs playground runs real Python compilation and stock browser-hosted Pyright.
Its language intelligence must represent VS Code using the same public types and
equivalent checker settings. Do not mock completions or rewrite, group, or suppress
diagnostics for a browser-only improvement. Improve the Python typing contract or
upstream checker instead; retain honest limitations where portable typing cannot
resolve them.
