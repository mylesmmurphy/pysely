# ADR 0005: User-provided database resources

Status: accepted.

## Resource inputs

| Dialect | Accepts |
| --- | --- |
| PostgreSQL / MySQL | A pool or async pool factory |
| SQLite | A connection or async connection factory |

Dialects do not accept connection settings or create resources themselves.

## Ownership

Pysely closes the configured pool or connection when the client is destroyed.
Applications must account for that ownership when sharing resources.

## Transactions

MySQL and SQLite resources must enable autocommit for root-level writes.
Explicit Pysely transactions still issue begin, commit, and rollback.
