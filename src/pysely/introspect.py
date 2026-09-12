"""Write annotated table classes from a live database.

``pysely introspect`` reads the catalog and emits the same ``tables.py`` a user
would write by hand, so ``pysely codegen`` and the rest of the pipeline do not
care where the tables came from. Connection details never reach the output.

Nullability becomes ``X | None``. Defaults, generated columns, primary keys and
foreign keys are recorded as comments: typed writes are not implemented yet,
so the annotation describes what a select reads back, not what an insert may
omit. Enum columns become ``Literal[...]``. A SQL type with no known Python
counterpart is an error unless ``--unknown object`` is given.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

from pysely.codegen import SchemaError

Record = Mapping[str, Any]
"""A catalog row from a driver; drivers are untyped, so values are ``Any``."""


class _PostgresConnection(Protocol):
    async def fetch(self, query: str, *args: object) -> Sequence[Record]: ...

    async def close(self) -> None: ...


class _MysqlCursor(Protocol):
    async def execute(self, query: str, args: object = None) -> object: ...

    async def fetchall(self) -> Sequence[Sequence[Any]]: ...

    async def __aenter__(self) -> _MysqlCursor: ...

    async def __aexit__(self, *exc_info: object) -> None: ...


class _MysqlConnection(Protocol):
    def cursor(self) -> _MysqlCursor: ...

    async def ensure_closed(self) -> None: ...


@dataclass(frozen=True, slots=True)
class IntrospectedColumn:
    name: str
    sql_type: str
    nullable: bool
    default: str | None = None
    generated: bool = False
    primary_key: bool = False
    foreign_key: str | None = None
    """``table.column`` this column references."""
    enum_values: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IntrospectedTable:
    name: str
    columns: tuple[IntrospectedColumn, ...]
    schema: str | None = None


@dataclass(frozen=True, slots=True)
class TypeMapping:
    """SQL type name (lower case, parameters stripped) to a Python annotation."""

    types: Mapping[str, str]
    imports: Mapping[str, str] = field(default_factory=dict[str, str])
    """Python annotation to the import line it needs."""


STANDARD_IMPORTS = {
    "date": "from datetime import date",
    "datetime": "from datetime import datetime",
    "time": "from datetime import time",
    "timedelta": "from datetime import timedelta",
    "Decimal": "from decimal import Decimal",
    "UUID": "from uuid import UUID",
}

SQLITE_TYPES = TypeMapping(
    {
        "integer": "int",
        "int": "int",
        "bigint": "int",
        "smallint": "int",
        "tinyint": "int",
        "boolean": "bool",
        "bool": "bool",
        "real": "float",
        "double": "float",
        "float": "float",
        "numeric": "float",
        "decimal": "float",
        "text": "str",
        "varchar": "str",
        "char": "str",
        "clob": "str",
        "blob": "bytes",
        "date": "str",
        "datetime": "str",
        "timestamp": "str",
        "json": "str",
    },
    STANDARD_IMPORTS,
)

POSTGRES_TYPES = TypeMapping(
    {
        "integer": "int",
        "int4": "int",
        "int2": "int",
        "smallint": "int",
        "bigint": "int",
        "int8": "int",
        "serial": "int",
        "bigserial": "int",
        "boolean": "bool",
        "bool": "bool",
        "real": "float",
        "float4": "float",
        "double precision": "float",
        "float8": "float",
        "numeric": "Decimal",
        "decimal": "Decimal",
        "money": "Decimal",
        "text": "str",
        "character varying": "str",
        "varchar": "str",
        "character": "str",
        "char": "str",
        "citext": "str",
        "uuid": "UUID",
        "bytea": "bytes",
        "date": "date",
        "time without time zone": "time",
        "time with time zone": "time",
        "time": "time",
        "timestamp without time zone": "datetime",
        "timestamp with time zone": "datetime",
        "timestamp": "datetime",
        "timestamptz": "datetime",
        "interval": "timedelta",
        "json": "object",
        "jsonb": "object",
    },
    STANDARD_IMPORTS,
)

MYSQL_TYPES = TypeMapping(
    {
        "int": "int",
        "integer": "int",
        "tinyint": "int",
        "smallint": "int",
        "mediumint": "int",
        "bigint": "int",
        "bit": "int",
        "bool": "bool",
        "boolean": "bool",
        "float": "float",
        "double": "float",
        "real": "float",
        "decimal": "Decimal",
        "numeric": "Decimal",
        "char": "str",
        "varchar": "str",
        "text": "str",
        "tinytext": "str",
        "mediumtext": "str",
        "longtext": "str",
        "binary": "bytes",
        "varbinary": "bytes",
        "blob": "bytes",
        "tinyblob": "bytes",
        "mediumblob": "bytes",
        "longblob": "bytes",
        "date": "date",
        "time": "timedelta",
        "datetime": "datetime",
        "timestamp": "datetime",
        "year": "int",
        "json": "object",
    },
    STANDARD_IMPORTS,
)

MAPPINGS = {"sqlite": SQLITE_TYPES, "postgres": POSTGRES_TYPES, "mysql": MYSQL_TYPES}

Unknown = Literal["fail", "object"]


def _base_type(sql_type: str) -> str:
    """``VARCHAR(255)`` -> ``varchar``; ``timestamp(3) with time zone`` keeps words."""
    lowered = sql_type.strip().lower()
    lowered = re.sub(r"\([^)]*\)", "", lowered)
    lowered = lowered.replace(" unsigned", "").replace(" zerofill", "")
    return re.sub(r"\s+", " ", lowered).strip()


def _class_name(table: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", table)
    return "".join(word[:1].upper() + word[1:] for word in words) + "Table"


def _attribute(table: str) -> str:
    name = re.sub(r"\W", "_", table)
    if not name.isidentifier() or name[:1].isdigit():
        name = f"t_{name}"
    return name


def render_tables(
    tables: Sequence[IntrospectedTable],
    mapping: TypeMapping,
    *,
    dialect: str,
    overrides: Mapping[str, str] | None = None,
    unknown: Unknown = "fail",
    schema_class: str = "DatabaseSchema",
) -> str:
    """Emit ``tables.py`` source for the introspected tables."""
    overrides = dict(overrides or {})
    imports: set[str] = set()
    literal_needed = False
    problems: list[str] = []
    classes: list[str] = []
    seen_attributes: dict[str, str] = {}
    for table in tables:
        attribute = _attribute(table.name)
        if attribute in seen_attributes:
            problems.append(
                f"tables {seen_attributes[attribute]!r} and {table.name!r} both map "
                f"to attribute {attribute!r}; introspect one schema at a time"
            )
        seen_attributes[attribute] = table.name
        lines = [f"class {_class_name(table.name)}:"]
        if table.schema:
            lines.append(f"    # {table.schema}.{table.name}")
        for column in table.columns:
            key = f"{table.name}.{column.name}"
            if key in overrides:
                annotation = overrides.pop(key)
            elif column.enum_values:
                values = ", ".join(f'"{value}"' for value in column.enum_values)
                annotation = f"Literal[{values}]"
                literal_needed = True
            else:
                base = mapping.types.get(_base_type(column.sql_type))
                if base is None:
                    if unknown == "fail":
                        problems.append(
                            f"{key}: no Python type for {column.sql_type!r}; pass "
                            f"--override {key}=<annotation> or --unknown object"
                        )
                        continue
                    annotation = "object"
                else:
                    annotation = base
            for name, line in mapping.imports.items():
                if re.search(rf"\b{name}\b", annotation):
                    imports.add(line)
            if column.nullable and annotation != "object":
                annotation = f"{annotation} | None"
            notes: list[str] = []
            if column.primary_key:
                notes.append("primary key")
            if column.foreign_key:
                notes.append(f"references {column.foreign_key}")
            if column.generated:
                notes.append("generated")
            elif column.default is not None:
                notes.append(f"default {column.default}")
            comment = f"  # {'; '.join(notes)}" if notes else ""
            name = column.name
            if not name.isidentifier():
                problems.append(f"{key}: column name is not a Python identifier")
                continue
            lines.append(f"    {name}: {annotation}{comment}")
        if len(lines) == 1 or (len(lines) == 2 and table.schema):
            problems.append(f"table {table.name!r} has no usable columns")
        classes.append("\n".join(lines))
    if overrides:
        problems.append(
            "overrides for unknown columns: " + ", ".join(sorted(overrides))
        )
    if problems:
        raise SchemaError("\n".join(problems))
    if literal_needed:
        imports.add("from typing import Literal")
    header = [
        f'"""Written by `pysely introspect` ({dialect}). Edit, or regenerate."""',
        "",
    ]
    if imports:
        header += [*sorted(imports), ""]
    body = "\n\n\n".join(classes)
    schema = [f"class {schema_class}:"] + [
        f"    {_attribute(table.name)}: {_class_name(table.name)}" for table in tables
    ]
    return "\n".join(header) + "\n" + body + "\n\n\n" + "\n".join(schema) + "\n"


# --- catalog readers --------------------------------------------------------


def introspect_sqlite(path: str) -> list[IntrospectedTable]:
    connection = sqlite3.connect(path)
    try:
        names = [
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table' "
                "and name not like 'sqlite_%' order by name"
            )
        ]
        tables: list[IntrospectedTable] = []
        for name in names:
            foreign: dict[str, str] = {}
            for row in connection.execute(f'pragma foreign_key_list("{name}")'):
                foreign[str(row[3])] = f"{row[2]}.{row[4]}"
            columns = [
                IntrospectedColumn(
                    name=str(row[1]),
                    sql_type=str(row[2]) or "text",
                    nullable=not row[3] and not row[5],
                    default=str(row[4]) if row[4] is not None else None,
                    primary_key=bool(row[5]),
                    foreign_key=foreign.get(str(row[1])),
                )
                for row in connection.execute(f'pragma table_info("{name}")')
            ]
            tables.append(IntrospectedTable(name, tuple(columns)))
        return tables
    finally:
        connection.close()


async def introspect_postgres(
    dsn: str, schema: str = "public"
) -> list[IntrospectedTable]:
    import asyncpg  # type: ignore[import-not-found]  # optional driver

    connect = cast(
        Callable[[str], Awaitable[_PostgresConnection]],
        asyncpg.connect,  # pyright: ignore[reportUnknownMemberType]
    )
    connection = await connect(dsn)
    try:
        rows = await connection.fetch(
            """
            select c.table_name, c.column_name, c.data_type, c.udt_name,
                   c.is_nullable = 'YES' as nullable, c.column_default,
                   c.is_generated = 'ALWAYS' or c.is_identity = 'YES' as generated,
                   c.ordinal_position
            from information_schema.columns c
            join information_schema.tables t
              on t.table_schema = c.table_schema and t.table_name = c.table_name
            where c.table_schema = $1 and t.table_type = 'BASE TABLE'
            order by c.table_name, c.ordinal_position
            """,
            schema,
        )
        keys = await connection.fetch(
            """
            select tc.table_name, kcu.column_name, tc.constraint_type,
                   ccu.table_name as foreign_table, ccu.column_name as foreign_column
            from information_schema.table_constraints tc
            join information_schema.key_column_usage kcu
              on kcu.constraint_name = tc.constraint_name
             and kcu.table_schema = tc.table_schema
            left join information_schema.constraint_column_usage ccu
              on ccu.constraint_name = tc.constraint_name
             and tc.constraint_type = 'FOREIGN KEY'
            where tc.table_schema = $1
              and tc.constraint_type in ('PRIMARY KEY', 'FOREIGN KEY')
            """,
            schema,
        )
        enums = await connection.fetch(
            """
            select t.typname, e.enumlabel
            from pg_type t join pg_enum e on e.enumtypid = t.oid
            order by t.typname, e.enumsortorder
            """
        )
    finally:
        await connection.close()
    primary: set[tuple[str, str]] = set()
    foreign: dict[tuple[str, str], str] = {}
    for key in keys:
        pair = (key["table_name"], key["column_name"])
        if key["constraint_type"] == "PRIMARY KEY":
            primary.add(pair)
        elif key["foreign_table"]:
            foreign[pair] = f"{key['foreign_table']}.{key['foreign_column']}"
    labels: dict[str, list[str]] = {}
    for enum in enums:
        labels.setdefault(enum["typname"], []).append(enum["enumlabel"])
    grouped: dict[str, list[IntrospectedColumn]] = {}
    for row in rows:
        pair = (row["table_name"], row["column_name"])
        sql_type = row["data_type"]
        enum_values: tuple[str, ...] = ()
        if sql_type == "USER-DEFINED" and row["udt_name"] in labels:
            enum_values = tuple(labels[row["udt_name"]])
            sql_type = row["udt_name"]
        grouped.setdefault(row["table_name"], []).append(
            IntrospectedColumn(
                name=row["column_name"],
                sql_type=sql_type,
                nullable=bool(row["nullable"]),
                default=row["column_default"],
                generated=bool(row["generated"]),
                primary_key=pair in primary,
                foreign_key=foreign.get(pair),
                enum_values=enum_values,
            )
        )
    return [
        IntrospectedTable(name, tuple(columns), schema)
        for name, columns in grouped.items()
    ]


async def introspect_mysql(database: str, **connect: Any) -> list[IntrospectedTable]:
    import asyncmy  # type: ignore[import-not-found]  # optional driver

    open_connection = cast(
        Callable[..., Awaitable[_MysqlConnection]],
        asyncmy.connect,  # pyright: ignore[reportUnknownMemberType]
    )
    connection = await open_connection(db=database, **connect)
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                select c.table_name, c.column_name, c.data_type, c.column_type,
                       c.is_nullable = 'YES', c.column_default, c.extra, c.column_key
                from information_schema.columns c
                join information_schema.tables t
                  on t.table_schema = c.table_schema and t.table_name = c.table_name
                where c.table_schema = %s and t.table_type = 'BASE TABLE'
                order by c.table_name, c.ordinal_position
                """,
                (database,),
            )
            rows = await cursor.fetchall()
            await cursor.execute(
                """
                select table_name, column_name, referenced_table_name,
                       referenced_column_name
                from information_schema.key_column_usage
                where table_schema = %s and referenced_table_name is not null
                """,
                (database,),
            )
            references = await cursor.fetchall()
    finally:
        await connection.ensure_closed()
    foreign = {(str(row[0]), str(row[1])): f"{row[2]}.{row[3]}" for row in references}
    grouped: dict[str, list[IntrospectedColumn]] = {}
    for row in rows:
        table, column, data_type, column_type, nullable, default, extra, key = row
        enum_values: tuple[str, ...] = ()
        if str(data_type).lower() == "enum":
            enum_values = tuple(re.findall(r"'((?:[^']|'')*)'", str(column_type)))
        generated = "generated" in str(extra).lower() or "auto_increment" in str(extra)
        grouped.setdefault(str(table), []).append(
            IntrospectedColumn(
                name=str(column),
                sql_type=str(data_type),
                nullable=bool(nullable),
                default=str(default) if default is not None else None,
                generated=generated,
                primary_key=str(key) == "PRI",
                foreign_key=foreign.get((str(table), str(column))),
                enum_values=enum_values,
            )
        )
    return [
        IntrospectedTable(name, tuple(columns), database)
        for name, columns in grouped.items()
    ]


def parse_overrides(items: Iterable[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in items:
        key, separator, annotation = item.partition("=")
        if not separator or key.count(".") != 1 or not annotation:
            raise SchemaError(f"override must look like table.column=Type: {item!r}")
        overrides[key] = annotation
    return overrides
