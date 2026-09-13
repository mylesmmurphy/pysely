# Typgen optimization experiments

Baseline: `748fed4305f12b5bc45088b9dc0f22612af6311a`.
See [raw measurements](results.json) for the environment and individual runs.

## Kept

- One projection overload for already-nullable columns and value groups.
- Direct stub rendering: no runtime twins, nested-field IR, or lowering pass.
- Linear method counting when removing single-signature overload decorators.

| Generation only | Before | After |
| --- | --- | --- |
| 20-table stub | 581,860 bytes | 557,334 bytes |
| 20-table generation | 2.409 s | 1.352 s |
| 100-table stub | 2,915,524 bytes | 2,789,230 bytes |
| 100-table generation | 28.930 s | 7.779 s |

The 100-table run does not establish checker or editor performance at that size.

## Rejected: merging projection mappings across tables

Two reduced prototypes are retained as text fixtures:

- `union-receiver.py.txt`: both checkers accept the unjoined `b.id` selection.
  Unioning receivers loses the connection between table scope and the selected name.
- `bounded-key.py.txt`: both checkers reject the valid joined `b.name` selection.
  A bounded method type variable in the scope receiver does not infer the needed subset.

Copy a fixture to a temporary `.py` file and run stock Pyright and strict mypy.
These are failed experiments, not part of the shipped interface or a proof that
every possible grouping strategy is impossible.

## Rejected: aliases for repeated column-state unions

The candidate defined `_TableG0`-style aliases for qualified column unions.
It replaced repeated literals in join returns and single-table base classes.

Expanded aliases reproduced the direct renderer's declarations exactly.
Output fell to 525,828 bytes without changing the 1,852 overloads.

| Paired run, five edits | Direct | Aliased |
| --- | --- | --- |
| Median two-table completion | 593 ms | 790 ms |
| Median three-table completion | 962 ms | 1,217 ms |
| Cold mypy | 45.12 s | 40.44 s |

The smaller file helped the cold checker but slowed joined completions in this run.
It was not kept. Timings vary; these are local measurements, not statistical guarantees.

## Verification

- Both checkers validate the generated interfaces and the existing positive/negative fixtures.
- A new matrix selects nullable fields before further joins and checks all four join kinds.
- Negative cases still reject unjoined columns, ambiguous names, wrong values, and missing keys.
- The direct renderer matched the previous declarations apart from import ordering.

Reproduce the accepted checker/editor measurements:

```sh
uv run python scripts/benchmark_typing.py --tables 20 --rounds 5
uv run pytest test/typgen test/typings
```

Exact selection still generates per-column mappings. This pass improves it; it
does not remove that scaling limit or change the public query API.
