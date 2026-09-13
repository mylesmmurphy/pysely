# Queries

Start with a client from `DatabaseSchema.connect(dialect=dialect)`.
These examples use the [playground's person and pet schema](assets/examples/schema.py).

Run examples containing `await` inside an async function. Database tables must already exist.

## Select columns

```python
query = (
    db.select_from("person")
    .select("id")
    .select("first_name")
    .where("first_name", "=", "Ada")
)
```

Use one `.select()` per column to keep exact result keys and types.
Building a query does not execute it.

| Finish with | Result |
| --- | --- |
| `query.compile()` | SQL and parameters; no connection needed |
| `await query.execute()` | A list of rows, possibly empty |
| `await query.execute_take_first()` | A row or `None` |
| `await query.execute_take_first_or_throw()` | A row, or `NoResultError` |

Use `.limit(1)` if the database should fetch at most one row.

```python
compiled = query.compile()
print(compiled.sql)
print(compiled.parameters)
```

Values are sent separately from SQL. Do not interpolate user input into SQL strings.

## Rename a result key

```python
row = await (
    db.select_from("pet")
    .select_as("name", "pet_name")
    .execute_take_first_or_throw()
)
name = row["pet_name"]  # str
```

Use a literal alias with `select_as`. The string form `"name as pet_name"`
works at runtime but does not preserve exact static result typing.

Rows are immutable mappings. Call `row.to_dict()` for an ordinary dictionary.

## Filter rows

```python
query = (
    db.select_from("person")
    .select("id")
    .where("status", "=", "active")
    .where("first_name", "like", "A%")
)
```

Repeated `where` calls are joined with SQL `AND`.

| Operator | Value |
| --- | --- |
| `=`, `!=`, `<>`, `<`, `<=`, `>`, `>=` | The column's Python type |
| `is`, `is not` | `None` |
| `like`, `not like` | A string pattern, for string columns |
| `in`, `not in` | A list or tuple of column values |

Use `is` or `is not` to compare with SQL `NULL`.

## Group conditions

`eb` is an expression builder. Call it like `where`, then combine conditions:

```python
query = (
    db.select_from("pet")
    .select("name")
    .where(
        lambda eb: eb.or_(
            eb("species", "=", "cat"),
            eb("species", "=", "dog"),
        )
    )
)
```

Use `eb.and_()`, `eb.or_()`, and `eb.not_()` for nested conditions.
Callback columns and values receive the same checks as `where`.

## Join tables

```python
query = (
    db.select_from("person")
    .left_join("pet", "person.id", "pet.owner_id")
    .select("person.id")
    .select("first_name")
    .select_as("pet.name", "pet_name")
)
```

Each join takes the new table and two columns to compare with `=`.
Write joins directly in Python; nothing needs to be declared to `typgen`.

- `inner_join`: return matching rows.
- `left_join`: keep left rows; the joined table's values may be `None`.
- `right_join` and `full_join`: typing conservatively allows `None` for every field.

MySQL does not support full joins. Qualify shared column names, such as `person.id`.

### Compare two columns

```python
query = query.where_ref("person.id", "=", "pet.owner_id")
```

`where` binds a value. `where_ref` compares columns; `eb.ref()` does the same inside a callback.

## Order and page

```python
query = (
    db.select_from("person")
    .select("id")
    .order_by("id", "asc")
    .limit(10)
    .offset(20)
)
```

`order_by` accepts a column or selected alias. Use a stable, unique ordering when paging.
SQL Server requires ordering for `offset ... fetch`.

## Group rows

```python
query = (
    db.select_from("person")
    .select("status")
    .group_by("status")
    .having(lambda eb: eb("status", "!=", "inactive"))
)
```

`where` filters before grouping. `having` filters groups and takes a callback.
Selected non-aggregate columns must appear in `group_by`.

## Combine queries

```python
names = (
    db.select_from("person")
    .select("first_name")
    .union(db.select_from("pet").select_as("name", "first_name"))
)
```

Both queries must select matching keys and types in the same order.
Also available: `union_all`, `intersect`, and `except_`.

## Insert, update, and delete

String-based writes work at runtime. Schema-specific static checking of write
keys and values is not implemented yet.

```python
await (
    db.insert_into("person")
    .values({"first_name": "Ada", "status": "active"})
    .execute()
)

await (
    db.update_table("person")
    .set({"first_name": "Ada"})
    .where("id", "=", 1)
    .execute()
)

await db.delete_from("person").where("id", "=", 1).execute()
```

Supply all values required by your database unless it provides defaults.
An update or delete without `where` affects every row.

### Return inserted values

```python
inserted = await (
    db.insert_into("person")
    .values({"first_name": "Ada", "status": "active"})
    .returning(["id", "first_name"])
    .execute_take_first_or_throw()
)
```

MySQL does not support `returning()` through this API.
Without it, writes return affected-row metadata; inserts can also report an insert ID.

## Use a transaction

```python
async with db.transaction() as tx:
    await (
        tx.update_table("person")
        .set({"status": "inactive"})
        .where("id", "=", 1)
        .execute()
    )
    await tx.delete_from("pet").where("owner_id", "=", 1).execute()
```

The block commits on success and rolls back on an exception.
Use `tx`, not `db`, so both queries share the transaction's connection.

## Reuse one connection

```python
async with db.connection() as connection_db:
    first = await connection_db.select_from("person").select("id").execute()
    second = await connection_db.select_from("pet").select("name").execute()
```

This reserves one connection for the block. It does not start a transaction.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Getting started](getting-started.md){ .md-button }
[Schema and typing →](typing.md){ .md-button .md-button--primary }

</nav>
