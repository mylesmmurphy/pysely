# ADR 0004: PGlite is a first-party dialect target

Status: accepted

PGlite receives PostgreSQL-compatible compiler support immediately and remains a
first-party runtime target. Its runtime adapter follows MSSQL in stage 2 because the
official implementation is JavaScript/WASM and the available native-language binding
repository currently labels its Python gateway work in progress. We will not make a
JavaScript runtime a core Python dependency or claim runtime support through the
PostgreSQL compiler alone.

References:

- https://github.com/electric-sql/pglite
- https://github.com/electric-sql/pglite-bindings
