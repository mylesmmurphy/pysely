# ADR 0003: Portable and enhanced typing

Status: accepted

Generated schema-specific clients are the default typing architecture. They use
ordinary `Literal` types, overloads, and generic query scope so standard Python
language servers can complete tables and currently available columns without a
Pysely editor extension.

The reusable runtime remains schema-independent. Generated clients wrap it and do
not duplicate SQL construction or execution. Strict generated entry points avoid a
blanket `str` overload because that would accept misspellings and suppress useful
literal completion.

Arbitrary projection aliases and some column-to-value relationships remain beyond
the current portable contract. The optional `pysely.mypy` plugin may provide
stronger checks, but it is not a runtime dependency or a baseline release gate.

The docs playground runs real Python and Pysely compilation but does not simulate
language-server results. Browser-hosted Pyright can be reconsidered when a current,
maintained build can be loaded without degrading startup.
