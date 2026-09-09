# ADR 0005: User-provided database resources

Status: accepted

PostgreSQL and MySQL dialects accept a pool or an async pool factory. The SQLite
dialect accepts a database connection or an async database factory. Dialects do
not accept connection settings or create these resources themselves.

Pysely closes its configured pool or database when destroyed, matching Kysely's
lifecycle. MySQL and SQLite resources must enable autocommit so root writes do not
leave implicit transactions open; explicit transactions still issue begin, commit,
and rollback.
