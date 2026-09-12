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

- `execute_take_first()` returns zero or one row.
- `execute_take_first_or_throw()` raises when no row exists.
- Pass `schema=Database` for schema-aware string queries.
- Qualify ambiguous columns with their table or alias.

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

## Boolean groups and column references

```python
query = (
    db.select_from("person")
    .inner_join("pet", "person.id", "pet.owner_id")
    .select("person.id")
    .where(
        lambda eb: eb.and_(
            eb("person.id", "!=", 0),
            eb.or_(
                eb("species", "=", "cat"),
                eb("species", "=", "dog"),
            ),
        ),
    )
)

reference_query = query.where_ref("person.id", "=", "pet.owner_id")
```

The expression builder uses the columns in the current query scope, so its string
arguments receive the same completion and type checking as `.where()`. Use
`.where_ref()` when both sides of a comparison are columns; `eb.not_()` and
`eb.ref()` are also available inside a callback.

Operators take different value shapes: comparisons bind the column's type,
`is`/`is not` take `None`, `like`/`not like` take a string on string columns,
and `in`/`not in` take a list or tuple.

## Joins

```python
query = (
    db.select_from("person")
    .left_join("pet", "pet.owner_id", "person.id")
    .select("first_name")
    .select("pet.name")  # str | None: the pet may be missing
)
```

`inner_join`, `left_join`, `right_join` and `full_join` take the table and the
two ON columns. After a left join the joined table's columns read as
nullable; after a right or full join every column does. MySQL has no full
join. Rows are immutable mappings; use `row.to_dict()` for a dictionary.

## Ordering, paging, grouping and set operations

```python
query = (
    db.select_from("person")
    .select("status")
    .select_as("person.id", "pid")
    .group_by("status")
    .having(lambda eb: eb("status", "!=", "inactive"))
    .order_by("pid", "desc")
    .limit(10)
    .offset(20)
)
names = (
    db.select_from("person")
    .select("first_name")
    .union(db.select_from("pet").select_as("name", "first_name"))
)
```

- `order_by` accepts a column in scope or the alias of a selected field.
- `having` takes a callback with the same operator shapes as `where`.
- `union`, `union_all`, `intersect` and `except_` require the other query to
  select the same keys with the same types.
- SQL Server pages with `offset ... fetch`, which requires `order_by`.

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

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Getting started](getting-started.md){ .md-button }
[Schema and typing →](typing.md){ .md-button .md-button--primary }

</nav>
