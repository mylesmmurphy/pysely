# ADR 0006: Generated typed interfaces

Status: superseded by [ADR 0007](0007-type-only-typgen.md).

This page records the old generated-runtime design.
For current usage, read [Type generation](../typgen.md).

## Problem

The mypy plugin and the playground's handwritten interface could drift.
A single generated interface could serve both mypy and Pyright.

## Historical decision

- Generate table declarations, runtime query wrappers, and type overloads together.
- Use one query class per table and a generic class for joined queries.
- Keep heavy annotations under `TYPE_CHECKING`, beside runtime implementations.
- Parse schema declarations without importing or executing them.
- Commit generated output and check freshness in CI.
- Remove the mypy plugin.

The old command was `pysely codegen tables.py --output schema.py`.
It is no longer supported.

## Historical type representation

### Scope

Single-table queries accepted qualified and unqualified column names.
Joined queries tracked tables, columns, and nullable tables with generic arguments.

Shared column names needed qualification after a join.

### Rows

Selected fields formed a nested list of `Cons[key, value, rest]` types.
A shared row class provided 16 positions of typed key lookup.

Left joins added nullability at selection time.
Right/full joins marked every result value as nullable.

### Predicates

Overloads were grouped by table, column value type, and operator family.
Callback expression builders repeated the same groups.

## Alternatives tested at the time

| Experiment | Result |
| --- | --- |
| Row type parameters grouped by value type | 20+ parameters per overload; 2.9 MB for 20 tables; no speedup |
| Table tokens in nested row fields | mypy inferred every key as nullable |
| Generic field unions | Both checkers bound the key to the first union member |
| One query class per table pair | Quadratic class growth |
| Joined overloads on per-table bases | Still evaluated on each edit |

These results describe the old representation, not a ban on future experiments.

## Historical measurements — September 11, 2026

Environment: macOS 14.6 x86_64, Python 3.11.4, Pyright 1.1.413, mypy 1.20.2.

Synthetic tables had 10–30 columns each, including six shared column names.

### Output and checks

| Tables / columns | Output | Definitions | Pyright warm | mypy cold / warm |
| --- | --- | --- | --- | --- |
| 20 / 333 | 1.3 MB | 3.3k | 3.1 s | 224 s / 0.3 s |
| 60 / 1,020 | 4.0 MB | 10.0k | 11.8 s | 607 s / 0.4 s |
| 100 / 1,693 | Refused | 17.2k | Not run | Not run |

The 20-table cold mypy run overlapped other work; an idle run took 13.6 seconds.
Generation and cold-check timings from that busy run were inflated.

### Select completion, p95

| Tables | Single table | Two joined tables | Three joined tables |
| --- | --- | --- | --- |
| 20 | 294 ms | 1.9 s | 2.8 s |
| 60 | 1.47 s | 8.2 s | 9.5 s |

The benchmark used `--tables 20 60 --rounds 10`.
The current benchmark script targets the replacement backend.

## Lessons

- Edit-time cache invalidation made reachable class definitions expensive.
- Joined selection scanned two overloads per column.
- The old module approached Pyright's analysis limit around 15,000 definitions.
- mypy's overlap checking and deeply nested row lookups were costly.

The old generator used `# mypy: ignore-errors` to bypass overlap checking.
That historical behavior is not the current stub validation strategy.

## Replacement

[ADR 0007](0007-type-only-typgen.md) removes generated runtime modules, shares
predicate generics, and replaces nested rows with flat field packs.

[Current measurements](../typing.md#performance) belong to that newer design.
