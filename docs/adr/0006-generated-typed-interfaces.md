# ADR 0006: Generated typed interfaces

Status: accepted. Supersedes the mypy plugin in [ADR 0003](0003-portable-typing.md).

## Context

Python has no `keyof` or mapped types, so a checker can only see
`Literal["species"]` if that literal exists in a real annotation. Two ways to
produce it: a mypy plugin, or generated source. Pyright has no plugin
interface, and Pylance is the primary editor target. Pysely shipped the plugin
and a separately hand-written interface for the playground; the two could
drift with nothing enforcing agreement.

## Decision

- `pysely codegen schema.py --output db.py` writes one self-contained module:
  the schema classes plus the typed interface. Applications import only `db.py`.
- The generator parses with `ast`; it never imports, executes, or connects.
- Output is committed; `--check` gates drift in CI and a pre-commit hook.
- The mypy plugin is removed.
- The schema may not define `Database` or `DatabaseQuery`.
- The playground regenerates `db.py` from the schema editor on every run.

## Consequences

One implementation serves both checkers. Static checking requires a generation
step; without it, runtime name validation still works. Value completion after a
join stays a superset (documented, not worked around). `pysely introspect` will
write the same module from a live database.
