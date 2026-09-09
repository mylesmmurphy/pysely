# ADR 0002: Driver-specific binding profiles

Status: accepted

The compiler receives a binding profile, not only a SQL dialect. PostgreSQL asyncpg
uses numbered `$n` placeholders, MySQL uses `%s`, and SQLite and aioodbc use `?`.
Compiled queries retain the profile name so incompatible execution can be rejected.

