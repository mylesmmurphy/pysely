# Queries

## Select

```python
query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .select("first_name")
    .select_as("pet.name", "pet_name")
    .where("species", "=", "dog")
)

compiled = query.compile()
rows = await query.execute()
```

Use `execute_take_first()` when zero or one row is expected, or
`execute_take_first_or_throw()` when a missing row is an error.

These queries use the schema passed as `schema=Database`; see
[Schema and typing](typing.md). Ambiguous columns must be qualified with their
table or alias. The object-based expression API remains available for queries that
use table and column objects. String writes use the same database schema and query
compiler.

### Portable typed aliases

Use `.select_as(source, alias)` when the result key should be inferred by standard
Python type checkers:

```python
row = await (
    db.select_from("pet")
    .select_as("pet.name", "pet_name")
    .execute_take_first_or_throw()
)
name = row["pet_name"]
```

Pysely separates these arguments because Python typing cannot split an arbitrary
`"pet.name as pet_name"` string into a source type and a new result key. The
single-string form remains supported at runtime, but exact portable result-key
inference is not promised for it. Direct literal aliases retain completion and
value information; dynamic or conflicting aliases use conservative result types.

## Object-based boolean groups and references

```python
from pysely import and_, or_

query = db.select_from(users).select(users.c.id).where(
    and_(
        users.c.id.ne(0),
        or_(
            users.c.nickname.is_null(),
            users.c.email.eq("ada@example.com"),
        ),
    )
)

reference_query = query.where_ref(users.c.email, "!=", users.c.nickname)
```

## Insert

```python
inserted = await (
    db.insert_into("person")
    .values({"first_name": "Ada"})
    .returning(["id", "first_name"])
    .execute_take_first_or_throw()
)
```

MySQL does not support `returning()` through this API. Non-returning inserts
provide affected-row and insert-ID metadata.

## Update and delete

```python
await (
    db.update_table("person")
    .set({"first_name": "Ada"})
    .where("id", "=", 1)
    .execute()
)

await db.delete_from("person").where("id", "=", 1).execute()
```

## Transactions

```python
async with db.transaction() as tx:
    await tx.insert_into("person").values({"first_name": "Ada"}).execute()
```

The transaction commits on normal exit and rolls back when the block raises.
Use the transaction client inside the block so every query uses the pinned
connection.

## Single-connection scope

```python
async with db.connection() as connection_db:
    first = await connection_db.select_from("person").select("id").execute()
    second = await connection_db.select_from("person").select("first_name").execute()
```
