from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pysely.codegen import SchemaError, generate, parse_schema

ROOT = Path(__file__).parents[2]
EXAMPLE_SCHEMA = ROOT / "docs/assets/examples/schema.py"
EXAMPLE_DATABASE = ROOT / "docs/assets/examples/database.py"

SCHEMA = """
from typing import Literal


class PersonTable:
    id: int
    name: str
    status: Literal["active", "inactive"]


class PetTable:
    id: int
    species: Literal["cat", "dog"]


class DatabaseSchema:
    person: PersonTable
    pet: PetTable
"""


def test_parses_tables_and_columns() -> None:
    model = parse_schema(SCHEMA)
    assert model.database == "DatabaseSchema"
    assert [table.attribute for table in model.tables] == ["person", "pet"]
    assert [column.name for column in model.tables[0].columns] == [
        "id",
        "name",
        "status",
    ]


def test_bare_names_are_omitted_when_ambiguous() -> None:
    model = parse_schema(SCHEMA)
    person, pet = model.tables
    # "id" exists on both tables, so only the qualified form is offered.
    assert model.references(person, "id") == ["person.id"]
    assert model.references(pet, "id") == ["pet.id"]
    assert model.references(person, "name") == ["person.name", "name"]


def test_generates_literal_aliases_and_value_types() -> None:
    generated = generate(SCHEMA)
    assert "PersonColumns: TypeAlias = Literal[" in generated
    assert '    "person.status",' in generated
    assert '    "status",' in generated
    # The column's value type reaches the where() overload.
    assert 'value: Literal["active", "inactive"],' in generated
    assert 'value: Literal["cat", "dog"],' in generated


def test_generation_is_deterministic() -> None:
    assert generate(SCHEMA) == generate(SCHEMA)


def test_rejects_a_module_without_a_database_class() -> None:
    with pytest.raises(SchemaError, match="No database class"):
        generate("class Lonely:\n    id: int\n")


def test_rejects_a_table_without_columns() -> None:
    source = "class Empty:\n    pass\n\n\nclass DB:\n    empty: Empty\n"
    with pytest.raises(SchemaError, match="no annotated columns"):
        generate(source)


def test_generated_example_is_committed_and_current() -> None:
    """The checked-in interface must match what the generator produces."""
    expected = generate(
        EXAMPLE_SCHEMA.read_text(),
        source_name=EXAMPLE_SCHEMA.name,
        output="docs/assets/examples/database.py",
    )
    assert EXAMPLE_DATABASE.read_text() == expected, (
        "docs/assets/examples/database.py is out of date; run "
        "`pysely codegen docs/assets/examples/schema.py "
        "--output docs/assets/examples/database.py`"
    )


def test_generated_output_passes_lint_and_format() -> None:
    ruff = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(EXAMPLE_DATABASE)],
        capture_output=True,
        text=True,
    )
    assert ruff.returncode == 0, ruff.stdout + ruff.stderr
    formatted = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", str(EXAMPLE_DATABASE)],
        capture_output=True,
        text=True,
    )
    assert formatted.returncode == 0, formatted.stdout + formatted.stderr


def test_cli_writes_and_detects_drift(tmp_path: Path) -> None:
    schema = tmp_path / "schema.py"
    schema.write_text(SCHEMA)
    output = tmp_path / "generated" / "db.py"

    missing = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysely.cli",
            "codegen",
            str(schema),
            "-o",
            str(output),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert missing.returncode == 1
    assert "does not exist" in missing.stderr

    written = subprocess.run(
        [sys.executable, "-m", "pysely.cli", "codegen", str(schema), "-o", str(output)],
        capture_output=True,
        text=True,
    )
    assert written.returncode == 0, written.stderr
    assert output.exists()

    current = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysely.cli",
            "codegen",
            str(schema),
            "-o",
            str(output),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert current.returncode == 0, current.stderr

    schema.write_text(
        SCHEMA.replace("    name: str\n", "    name: str\n    note: str\n")
    )
    stale = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysely.cli",
            "codegen",
            str(schema),
            "-o",
            str(output),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert stale.returncode == 1
    assert "out of date" in stale.stderr


def test_cli_reports_a_bad_schema(tmp_path: Path) -> None:
    schema = tmp_path / "schema.py"
    schema.write_text("class Lonely:\n    id: int\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysely.cli",
            "codegen",
            str(schema),
            "-o",
            str(tmp_path / "db.py"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "No database class" in result.stderr
