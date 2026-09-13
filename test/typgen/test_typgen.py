from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pysely.typgen import SchemaError, generate, parse_schema
from scripts.generate_flat_row import render as render_row

ROOT = Path(__file__).parents[2]
SCHEMA = """from typing import Literal, Optional
from pysely import SchemaDefinition

class PersonTable:
    id: int
    name: str
    nickname: Optional[str]
    status: Literal["active", "inactive"]

class PetTable:
    id: int
    owner_id: int
    name: str
    species: Literal["cat", "dog"]
    weight: float | None

class DatabaseSchema(SchemaDefinition):
    person: PersonTable
    pet: PetTable
"""


def test_parses_nullable_annotations_and_scope() -> None:
    model = parse_schema(SCHEMA)
    person, pet = model.tables
    assert (person.columns[2].value, person.columns[2].nullable) == ("str", True)
    assert (pet.columns[-1].value, pet.columns[-1].nullable) == ("float", True)
    union = parse_schema(SCHEMA.replace("Optional[str]", "Union[None, str]"))
    assert union.tables[0].columns[2].value == "str"
    assert model.spellings(person, "id") == ["person.id", "id"]
    assert model.references(person, "id") == ["person.id"]


def test_stub_is_deterministic_and_contains_only_type_declarations() -> None:
    stub = generate(SCHEMA)
    assert stub == generate(SCHEMA)
    assert "Cons[" not in stub
    assert "_QUERIES" not in stub
    assert "TYPE_CHECKING" not in stub
    assert "*FieldsT" in stub
    tree = ast.parse(stub)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            assert len(node.body) == 1
            assert isinstance(node.body[0], ast.Expr)
            assert isinstance(node.body[0].value, ast.Constant)
            assert node.body[0].value.value is Ellipsis
    predicates = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "_Predicates"
    )
    assert any(
        isinstance(n, ast.FunctionDef) and n.name == "where" for n in predicates.body
    )
    for cls in (
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name.endswith("Query")
    ):
        assert not any(
            isinstance(n, ast.FunctionDef) and n.name in {"where", "having"}
            for n in cls.body
        )


@pytest.mark.parametrize(
    "source, message",
    [
        ("class Lonely:\n    id: int\n", "No database class"),
        (SCHEMA.replace("(SchemaDefinition)", ""), "inherit SchemaDefinition"),
        (SCHEMA.replace("DatabaseSchema", "DatabaseClient"), "reserved"),
        (SCHEMA + '\nprint("do not execute")\n', "declarative"),
    ],
)
def test_rejects_invalid_schema(source: str, message: str) -> None:
    with pytest.raises(SchemaError, match=message):
        generate(source)


def test_never_generates_runtime_modules() -> None:
    with pytest.raises(SchemaError, match="only writes .pyi"):
        generate(SCHEMA, output="schema.py")


def test_cli_exposes_only_typgen_command() -> None:
    command = [sys.executable, "-m", "pysely.cli"]
    help_result = subprocess.run([*command, "--help"], capture_output=True, text=True)
    assert help_result.returncode == 0
    assert "typgen" in help_result.stdout
    assert "codegen" not in help_result.stdout
    old = subprocess.run([*command, "codegen"], capture_output=True, text=True)
    assert old.returncode == 2
    assert "invalid choice" in old.stderr


@pytest.mark.parametrize(
    "path",
    [
        "test/fixtures/schema.py",
        "docs/assets/examples/schema.py",
        "examples/stubs/dbschema.py",
    ],
)
def test_committed_stubs_are_current(path: str) -> None:
    source = ROOT / path
    assert source.with_suffix(".pyi").read_text() == generate(
        source.read_text(), source_name=path
    )


def test_shared_row_stub_is_current() -> None:
    assert (ROOT / "src/pysely/flat_row.pyi").read_text() == render_row()


def test_cli_adjacent_output_check_and_source_preservation(tmp_path: Path) -> None:
    source = tmp_path / "dbschema.py"
    source.write_text(SCHEMA)
    command = [sys.executable, "-m", "pysely.cli", "typgen", str(source)]
    assert subprocess.run([*command, "--check"], capture_output=True).returncode == 1
    assert subprocess.run(command, capture_output=True).returncode == 0
    assert source.read_text() == SCHEMA
    assert subprocess.run([*command, "--check"], capture_output=True).returncode == 0
    source.write_text(SCHEMA.replace("    name: str", "    name: bytes"))
    assert subprocess.run([*command, "--check"], capture_output=True).returncode == 1
    for output in (source, tmp_path / "different.pyi"):
        result = subprocess.run(
            [*command, "-o", str(output)], capture_output=True, text=True
        )
        assert result.returncode == 2
        assert "adjacent .pyi" in result.stderr
    assert source.read_text() != generate(SCHEMA)


def test_runtime_works_without_any_generated_file(tmp_path: Path) -> None:
    (tmp_path / "dbschema.py").write_text(SCHEMA)
    script = """from dbschema import DatabaseSchema
from pysely import Dialect
from pysely.query_compiler import BindingProfile
from pysely.schema_definition import SchemaClient, FlatQuery
import dbschema
assert not hasattr(dbschema, "DatabaseClient")
db = DatabaseSchema.connect(dialect=Dialect(BindingProfile("test", "?")))
assert type(db) is SchemaClient
q = (db.select_from("person").left_join("pet", "person.id", "pet.owner_id")
     .select_as("pet.name", "pet_name"))
assert type(q) is FlatQuery
assert 'left join' in q.compile().sql
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "dbschema.pyi").exists()


def check_both(folder: Path, filename: str) -> None:
    for command in (
        ["pyright", filename],
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", filename],
    ):
        result = subprocess.run(
            command,
            cwd=folder,
            capture_output=True,
            text=True,
            timeout=90,
            env={**os.environ, "MYPYPATH": str(ROOT / "src")},
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_fifty_fields_exact_select_aliases_and_outer_joins(tmp_path: Path) -> None:
    fields = "\n".join(f"    c{i}: {'str' if i % 2 else 'int'}" for i in range(50))
    source = (
        "from pysely import SchemaDefinition\nclass A:\n    id: int\n"
        + fields
        + "\nclass B:\n    id: int\n    owner_id: int\n    name: str\n"
        "class C:\n    id: int\n    owner_id: int\n    name: str\n"
        "class DatabaseSchema(SchemaDefinition):\n    a: A\n    b: B\n    c: C\n"
    )
    (tmp_path / "dbschema.py").write_text(source)
    (tmp_path / "dbschema.pyi").write_text(generate(source))
    setup = """from typing import assert_type
from dbschema import DatabaseSchema
from pysely import Dialect
from pysely.query_compiler import BindingProfile
db = DatabaseSchema.connect(dialect=Dialect(BindingProfile("test", "?")))
"""
    chain = 'db.select_from("a")' + "".join(
        f'.select("c{i}")' if i % 2 == 0 else f'.select_as("c{i}", "c{i}")'
        for i in range(50)
    )
    usage = (
        setup
        + "async def wide() -> None:\n    row = await ("
        + chain
        + ").execute_take_first_or_throw()\n"
    )
    usage += "".join(
        f'    assert_type(row["c{i}"], {"str" if i % 2 else "int"})\n'
        for i in range(50)
    )
    usage += """
async def joins() -> None:
    q = (db.select_from("a").left_join("b", "a.id", "b.owner_id")
         .left_join("c", "a.id", "c.owner_id"))
    r = await (q.select("a.id").select_as("b.name", "b_name")
               .select_as("c.name", "c_name").execute_take_first_or_throw())
    assert_type(r["id"], int)
    assert_type(r["b_name"], str | None)
    assert_type(r["c_name"], str | None)
    duplicate = await (db.select_from("a").select_as("c0", "key")
                       .select_as("c1", "key").execute_take_first_or_throw())
    assert_type(duplicate["key"], str)
    async with db.transaction() as tx:
        v = await tx.select_from("a").select("id").execute_take_first_or_throw()
        assert_type(v["id"], int)
    async with db.connection() as conn:
        v = await conn.select_from("a").select("id").execute_take_first_or_throw()
        assert_type(v["id"], int)
"""
    (tmp_path / "usage.py").write_text(usage)
    check_both(tmp_path, "usage.py")
    check_both(tmp_path, "dbschema.pyi")


def test_single_table_schema_has_valid_overloads(tmp_path: Path) -> None:
    source = (
        "from pysely import SchemaDefinition\nclass Person:\n    id: int\n"
        "class DB(SchemaDefinition):\n    person: Person\n"
    )
    (tmp_path / "dbschema.py").write_text(source)
    (tmp_path / "dbschema.pyi").write_text(generate(source))
    check_both(tmp_path, "dbschema.pyi")
