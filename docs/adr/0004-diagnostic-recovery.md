# ADR 0004: Honest editor diagnostics and error recovery

Status: investigated; retain stock diagnostics. Last checked: 2026-09-10.

The playground must expose the same language intelligence as VS Code with the
same public types and equivalent checker settings. No browser-only diagnostic
filtering, range rewriting, message shortening, or completion recovery. Execution
errors appear separately from type-checking diagnostics.

## Evidence

Checked with stock Pyright 1.1.413 and mypy 1.20.2, without the Pysely mypy plugin.
The reproducible fixture is `test/typings/diagnostic_recovery.txt`. Run from the
repository root; failures are intentional because the fixture compares invalid
calls and rejected signature designs:

```console
uv run pyright test/typings/diagnostic_recovery.txt
uv run mypy --strict --follow-imports=silent test/typings/diagnostic_recovery.txt
```

The actual generated client already preserves the query type after a misspelled
`where` column. Pyright reports the string argument's range, and mypy also retains
the query type. The previous whole-line highlight was a duplicate runtime marker
added by the playground. Removing that marker fixes the duplication without
changing language-server results.

A misspelled `inner_join` table fails overload resolution. Pyright reports both
the bad argument and the call, then uses `Unknown` for the result; later chained
members also report unknown types in strict mode. Mypy reports the overload failure
but uses `Any` for recovery. Fewer mypy errors do not mean preserved type safety.

## Signature experiments

| Approach | Observed result | Decision |
| --- | --- | --- |
| Literal overloads, reordered overloads | Pyright returns `Unknown`; mypy returns `Any` | Reordering changes the candidate error, not recovery |
| Final overload accepting only known table literals | Same failure and recovery | Keep rejecting unknown tables |
| Final overload with a bounded type variable | Same failure and recovery | Does not recover the chain |
| Overloads with identical return types | Still `Unknown` / `Any` | A common return type does not help |
| Concrete implementation with a known query return type | Still `Unknown` / `Any` | Implementation annotations are not call-site fallback signatures |
| Final `str` overload returning a query | Both accept the misspelled table | Reject: silently permits invalid queries |
| Final `str` overload returning `Never` | Accepts the misspelled call, makes continuation unreachable, and conflicts with other overload returns | Reject: hides mistakes |
| Single non-overloaded literal-union signature | Rejects typo and retains a query type | Loses table-dependent scope precision if used as a replacement |
| Single bounded generic signature | Rejects typo; Pyright recovers as `Query[Unknown]`, mypy as `Query[Literal['pett']]` | Can track table names, but does not map them to the column/result types required by the current API |

The single-signature designs are not equivalent replacements for joins. Returning
all schema columns would expose columns from unjoined tables; returning only the
old scope would omit newly joined columns. A generic table-name scope would still
need a portable mapping to column/value types and join nullability. Moving that
mapping into overloaded `where`/`select` methods merely moves the failure point and
can regress the existing recovery for bad columns. No such redesign is adopted
without proving scope safety, completion, and result inference in both checkers.

## Checker boundary

The pinned [Pyright overload resolver](https://github.com/microsoft/pyright/blob/71b0cbe75fb8c38b3278ef7c8db16d2f4492f592/packages/pyright-internal/src/analyzer/typeEvaluator.ts#L10941)
explicitly replaces the best failing overload's return type with `Unknown`.
The [typing specification](https://typing.python.org/en/latest/spec/overload.html)
excludes the implementation signature from call matching. Wrapping the same
overloads in a callable protocol or changing the runtime implementation does not
provide a separate recovery contract.

Disabling unknown-type diagnostics changes checker settings, not inference.
Deprecated broad fallbacks cannot enforce table validity in ordinary configurations
and still accept the argument. Custom plugins or a patched browser checker would
not meet the stock VS Code/Pylance requirement. Literal aliases help organize the
types, but the checker controls how their expansions appear in diagnostics.

No sound drop-in fix was found for failed joins with the current portable string
API. Keep the strict types and visible limitation. Revisit when upstream recovery
changes or a portable scope-mapping design has equivalent safety and editor tests.
The fixture is an investigation artifact, not a requirement to preserve noisy
diagnostics forever.
