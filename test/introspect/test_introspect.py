from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from pysely.codegen import SchemaError, generate
from pysely.introspect import (
    MYSQL_TYPES,
    POSTGRES_TYPES,
    SQLITE_TYPES,
    IntrospectedColumn,
    IntrospectedTable,
    introspect_sqlite,
    parse_overrides,
    render_tables,
)

ROOT = Path(__file__).parents[2]


def sqlite_fixture(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        create table person (
            id integer primary key,
            first_name text not null,
            last_name text,
            score real not null default 0
        );
        create table pet (
            id integer primary key,
            owner_id integer not null references person(id),
            name varchar(80) not null,
            born date
        );
        """
    )
    connection.close()


def test_sqlite_introspection_reads_types_nullability_and_keys(tmp_path: Path) -> None:
    sqlite_fixture(tmp_path / "app.db")
    tables = introspect_sqlite(str(tmp_path / "app.db"))
    assert [table.name for table in tables] == ["person", "pet"]
    person, pet = tables
    assert [
        (c.name, c.sql_type, c.nullable, c.primary_key) for c in person.columns
    ] == [
        ("id", "INTEGER", False, True),
        ("first_name", "TEXT", False, False),
        ("last_name", "TEXT", True, False),
        ("score", "REAL", False, False),
    ]
    assert person.columns[3].default == "0"
    assert pet.columns[1].foreign_key == "person.id"
    source = render_tables(tables, SQLITE_TYPES, dialect="sqlite")
    assert "class PersonTable:" in source
    assert "    id: int  # primary key" in source
    assert "    last_name: str | None" in source
    assert "    score: float  # default 0" in source
    assert "    owner_id: int  # references person.id" in source
    assert "    born: str | None" in source
    assert source.endswith(
        "class DatabaseSchema:\n    person: PersonTable\n    pet: PetTable\n"
    )
    # The output feeds the generator unchanged.
    generated = generate(source)
    assert "class PersonQuery(" in generated


def test_render_maps_enums_defaults_and_imports() -> None:
    tables = [
        IntrospectedTable(
            "order_line",
            (
                IntrospectedColumn(
                    "id", "bigint", False, generated=True, primary_key=True
                ),
                IntrospectedColumn(
                    "status", "order_status", False, enum_values=("new", "paid")
                ),
                IntrospectedColumn("total", "numeric", True),
                IntrospectedColumn("placed_at", "timestamp with time zone", False),
                IntrospectedColumn("payload", "jsonb", True),
            ),
            "public",
        )
    ]
    source = render_tables(tables, POSTGRES_TYPES, dialect="postgres")
    assert (
        "from decimal import Decimal" in source
        and "from datetime import datetime" in source
    )
    assert "from typing import Literal" in source
    assert "class OrderLineTable:\n    # public.order_line\n" in source
    assert "    id: int  # primary key; generated" in source
    assert '    status: Literal["new", "paid"]' in source
    assert "    total: Decimal | None" in source
    assert "    placed_at: datetime" in source
    assert "    payload: object" in source
    assert "    order_line: OrderLineTable" in source


def test_unknown_types_fail_unless_overridden_or_degraded() -> None:
    tables = [
        IntrospectedTable(
            "geo",
            (
                IntrospectedColumn("id", "int", False),
                IntrospectedColumn("shape", "geometry", True),
            ),
        )
    ]
    with pytest.raises(SchemaError, match="no Python type for 'geometry'"):
        render_tables(tables, MYSQL_TYPES, dialect="mysql")
    degraded = render_tables(tables, MYSQL_TYPES, dialect="mysql", unknown="object")
    assert "    shape: object" in degraded
    overridden = render_tables(
        tables, MYSQL_TYPES, dialect="mysql", overrides={"geo.shape": "bytes"}
    )
    assert "    shape: bytes | None" in overridden
    with pytest.raises(SchemaError, match="unknown columns: geo.missing"):
        render_tables(
            tables, MYSQL_TYPES, dialect="mysql", overrides={"geo.missing": "int"}
        )
    with pytest.raises(SchemaError, match="table.column=Type"):
        parse_overrides(["shape=bytes"])


def test_cli_writes_tables_from_sqlite_without_credentials(tmp_path: Path) -> None:
    sqlite_fixture(tmp_path / "app.db")
    output = tmp_path / "tables.py"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysely.cli",
            "introspect",
            "--dialect",
            "sqlite",
            "--url",
            str(tmp_path / "app.db"),
            "--override",
            "pet.born=date",
            "-o",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    source = output.read_text()
    assert str(tmp_path) not in source
    assert "from datetime import date" in source and "    born: date | None" in source
    generated = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysely.cli",
            "codegen",
            str(output),
            "-o",
            str(tmp_path / "schema.py"),
        ],
        capture_output=True,
        text=True,
    )
    assert generated.returncode == 0, generated.stderr
