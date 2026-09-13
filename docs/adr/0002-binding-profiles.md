# ADR 0002: Driver-specific binding profiles

Status: accepted.

## Decision

Compile with a driver binding profile, not just a SQL dialect.

| Driver | Placeholder |
| --- | --- |
| PostgreSQL / asyncpg | `$1`, `$2`, … |
| MySQL | `%s` |
| SQLite / aioodbc | `?` |

Compiled queries keep the profile name so incompatible execution can be rejected.
A compiler profile does not imply an available runtime adapter.
