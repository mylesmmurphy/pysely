# Queries

## Select

```python
query = (
    db.select_from("person")
    .inner_join("pet", "owner_id", "person.id")
    .select(["first_name", "pet.name as pet_name"])
    .where("species", "=", "dog")
)

compiled = query.compile()
rows = await query.execute()
```

Use `execute_take_first()` when zero or one row is expected, or
`execute_take_first_or_throw()` when a missing row is an error.

These queries use the schema passed as `schema=Database`; see
[Schema and typing](typing.md). Ambiguous columns must be qualified with their
table or alias. The remaining examples below document the earlier object-based
expression and write API while those operations move to the schema model.

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
    db.insert_into(users)
    .values({"email": "ada@example.com"})
    .returning(users.c.id, users.c.email)
    .execute_take_first_or_throw()
)
```

MySQL does not support `returning()` through this API. Non-returning inserts
provide affected-row and insert-ID metadata.

## Update and delete

```python
await (
    db.update_table(users)
    .set({"nickname": "Ada"})
    .where(users.c.id.eq(1))
    .execute()
)

await db.delete_from(users).where(users.c.id.eq(1)).execute()
```

## Transactions

```python
async with db.transaction() as tx:
    await tx.insert_into(users).values({"email": "ada@example.com"}).execute()
```

The transaction commits on normal exit and rolls back when the block raises.
Use the transaction client inside the block so every query uses the pinned
connection.

## Single-connection scope

```python
async with db.connection() as connection_db:
    first = await connection_db.select_from(users).select(users.c.id).execute()
    second = await connection_db.select_from(users).select(users.c.email).execute()
```
