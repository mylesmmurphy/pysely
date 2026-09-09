# ADR 0005: Explicit pool ownership

Status: accepted

PostgreSQL and MySQL dialects accept either a borrowed pool or settings used to
create an owned pool. Pysely closes only owned pools. MySQL pools must enable
autocommit so root writes do not leave implicit transactions on released
connections; explicit Pysely transactions still issue begin, commit, and rollback.

