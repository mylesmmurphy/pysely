# ADR 0006: Generated typed interfaces

Status: accepted

Supersedes the optional mypy plugin described in
[ADR 0003](0003-portable-typing.md).

## Context

Pysely's string-based API is modelled on Kysely, which relies on TypeScript's
`keyof`, mapped types, and indexed access types. Python has no equivalent. A
class annotated `species: Literal["cat", "dog"]` cannot be turned into
`Literal["species", "pet.species"]` at the type level, so for a checker to
reject `select("speces")` the literal must appear in a real annotation.

Two mechanisms can produce those annotations:

- A mypy plugin, which synthesises types during checking.
- Generated source, which both checkers read as ordinary code.

Pysely shipped the plugin, and separately maintained a hand-written typed
interface for the documentation playground because Pyright has no plugin
interface by design. Pylance is the primary editor target, so the plugin did not
serve it, and the two implementations of one rule set could disagree with
nothing enforcing agreement.

## Decision

Generate the typed interface with `pysely codegen` and remove the mypy plugin.

The generator parses the schema module with `ast`. It does not import it,
execute it, or connect to a database. Its output is committed so editors need no
build step, and `--check` gates drift in CI and in a pre-commit hook.

The output is one self-contained module. It re-emits the schema classes
alongside the typed interface rather than importing them, so an application
depends on a single generated file and the schema module's location is
irrelevant at runtime. A future `pysely introspect` will write the same module
directly from a live database. The schema may not define `Database` or
`DatabaseQuery`, which the generated module reserves for itself.

## Consequences

One implementation serves mypy and Pyright. The schema module is the single
source of truth for both runtime validation and static checking, and the
documentation playground regenerates the interface from the schema editor rather
than loading a file fixed at build time.

Users who want static checking run a generation step. Without it, annotated
schemas still validate names at runtime, and queries compile and execute
unchanged; only static checking is absent.

Value completion at the `where()` value position remains a superset after a
join, because Pyright gathers completions from every applicable overload without
narrowing on the column argument. Checking is unaffected. This is a limitation of
completion, not of the generated types, and is documented rather than worked
around.
