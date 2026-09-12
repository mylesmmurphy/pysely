from __future__ import annotations

import importlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from pysely.codegen import SchemaError, generate, parse_schema

ROOT = Path(__file__).parents[2]
GENERATED = {
    ROOT / "test/fixtures/schema.py": ROOT / "test/fixtures/tables.py",
    ROOT / "docs/assets/examples/schema.py": ROOT / "docs/assets/examples/tables.py",
}

SCHEMA = """
from typing import Literal, Optional


class PersonTable:
    id: int
    name: str
    nickname: Optional[str]
    status: Literal["active", "inactive"]


class PetTable:
    id: int
    species: Literal["cat", "dog"]
    weight: float | None


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
        "nickname",
        "status",
    ]


def test_splits_nullable_annotations_in_every_spelling() -> None:
    person, pet = parse_schema(SCHEMA).tables
    nickname = person.columns[2]
    assert (nickname.annotation, nickname.value, nickname.nullable) == (
        "Optional[str]",
        "str",
        True,
    )
    weight = pet.columns[2]
    assert (weight.value, weight.nullable) == ("float", True)
    union = parse_schema(SCHEMA.replace("Optional[str]", "Union[None, str]")).tables[0]
    assert (union.columns[2].value, union.columns[2].nullable) == ("str", True)


def test_shared_bare_names_are_scope_specific() -> None:
    model = parse_schema(SCHEMA)
    person, pet = model.tables
    # "id" exists on both tables: only the qualified form works in any scope.
    assert model.shared("id")
    assert model.references(person, "id") == ["person.id"]
    assert model.references(pet, "id") == ["pet.id"]
    assert model.references(person, "name") == ["person.name", "name"]
    generated = generate(SCHEMA)
    # ...but a single-table query still accepts the bare name.
    assert 'self, selections: Literal["person.id", "id"]' in generated


def test_generates_a_query_class_per_table_and_a_joined_class() -> None:
    generated = generate(SCHEMA)
    assert "class PersonQuery(" in generated and "class PetQuery(" in generated
    assert "class DatabaseQuery(" in generated
    # Single-table classes accept every spelling; the joined class only the
    # spellings that stay unambiguous.
    assert 'selections: Literal["person.id", "id"]' in generated
    assert 'selections: Literal["person.id"],' in generated
    assert "PersonScope: TypeAlias = Literal[" in generated
    assert 'Cons[Literal["id"], int, FieldsT]' in generated
    assert 'Cons[Literal["nickname"], Optional[str], FieldsT]' in generated
    assert 'Cons[Literal["nickname"], str | None, FieldsT]' in generated


def test_generates_value_types_per_operator_family() -> None:
    generated = generate(SCHEMA)
    assert 'value: Literal["active", "inactive"],' in generated
    assert 'operator: Literal["in", "not in"],' in generated
    assert (
        'value: list[Literal["cat", "dog"]] | tuple[Literal["cat", "dog"], ...]'
        in generated
    )
    assert 'operator: Literal["is", "is not"],' in generated
    assert "value: None," in generated
    like = 'operator: Literal["like", "not like"],'
    assert like in generated
    # LIKE is offered for string-like columns only.
    assert f'column: Literal["pet.weight", "weight"],\n            {like}' not in (
        generated
    )
    names = 'column: Literal["person.name", "name", "person.nickname", "nickname"],'
    assert f"{names}\n            {like}" in generated


def test_generation_is_deterministic() -> None:
    assert generate(SCHEMA) == generate(SCHEMA)


def test_rejects_a_module_without_a_database_class() -> None:
    with pytest.raises(SchemaError, match="No database class"):
        generate("class Lonely:\n    id: int\n")


def test_rejects_a_table_without_columns() -> None:
    source = "class Empty:\n    pass\n\n\nclass DB:\n    empty: Empty\n"
    with pytest.raises(SchemaError, match="no annotated columns"):
        generate(source)


@pytest.mark.parametrize(("output", "source"), GENERATED.items())
def test_generated_modules_are_committed_and_current(
    output: Path, source: Path
) -> None:
    """The checked-in modules must match what the generator produces."""
    relative_source = source.relative_to(ROOT)
    relative_output = output.relative_to(ROOT)
    expected = generate(
        source.read_text(),
        source_name=str(relative_source),
        output=str(relative_output),
    )
    assert output.read_text() == expected, (
        f"{relative_output} is out of date; run "
        f"`pysely codegen {relative_source} --output {relative_output}`"
    )


@pytest.mark.parametrize("output", GENERATED)
def test_generated_output_passes_lint_and_format(output: Path) -> None:
    for command in (["check"], ["format", "--check"]):
        result = subprocess.run(
            [sys.executable, "-m", "ruff", *command, str(output)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_cli_writes_and_detects_drift(tmp_path: Path) -> None:
    tables = tmp_path / "tables.py"
    tables.write_text(SCHEMA)
    output = tmp_path / "generated" / "schema.py"
    cli = [
        sys.executable,
        "-m",
        "pysely.cli",
        "codegen",
        str(tables),
        "-o",
        str(output),
    ]

    missing = subprocess.run([*cli, "--check"], capture_output=True, text=True)
    assert missing.returncode == 1
    assert "does not exist" in missing.stderr

    written = subprocess.run(cli, capture_output=True, text=True)
    assert written.returncode == 0
    assert output.read_text() == generate(
        SCHEMA, source_name=str(tables), output=str(output)
    )

    current = subprocess.run([*cli, "--check"], capture_output=True, text=True)
    assert current.returncode == 0

    tables.write_text(SCHEMA.replace("    id: int\n    name: str", "    id: int"))
    stale = subprocess.run([*cli, "--check"], capture_output=True, text=True)
    assert stale.returncode == 1
    assert "out of date" in stale.stderr


def test_cli_reports_a_bad_schema(tmp_path: Path) -> None:
    tables = tmp_path / "tables.py"
    tables.write_text("class Lonely:\n    id: int\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pysely.cli",
            "codegen",
            str(tables),
            "-o",
            str(tmp_path / "s.py"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "No database class" in result.stderr


def test_generated_module_is_self_contained(tmp_path: Path) -> None:
    """The output imports nothing from the table module and runs on its own."""
    generated = generate(SCHEMA)
    assert "from tables import" not in generated
    assert "class PersonTable:" in generated
    assert "class DatabaseSchema(GeneratedSchema[DatabaseClient]):" in generated
    assert "schema = DatabaseSchema" in generated

    module_path = tmp_path / "schema.py"
    module_path.write_text(generated)
    from pysely import Database, Dialect, Pysely
    from pysely.query_compiler import BindingProfile

    sys.path.insert(0, str(tmp_path))
    try:
        module = importlib.import_module("schema")
        db = Database(
            schema=module.schema, dialect=Dialect(BindingProfile("test", "?"))
        )
        assert type(db) is module.DatabaseClient
        assert isinstance(db, Pysely)
        assert module.PersonQuery is not module.DatabaseQuery
        query = db.select_from("pet").where("species", "=", "cat").select("pet.id")
        compiled = query.compile()
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("schema", None)

    assert compiled.sql == 'select "pet"."id" from "pet" where "species" = ?'
    assert compiled.parameters == ("cat",)


def test_generated_module_imports_in_a_fresh_process_and_package(
    tmp_path: Path,
) -> None:
    """Postponed annotations and TYPE_CHECKING twins survive a real import."""
    package = tmp_path / "app"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "schema.py").write_text(generate(SCHEMA, output="app/schema.py"))
    script = textwrap.dedent(
        """
        from app.schema import schema, DatabaseClient, PersonQuery
        from pysely import Database, Dialect
        from pysely.query_compiler import BindingProfile
        from pysely.schema import Schema

        db = Database(schema=schema, dialect=Dialect(BindingProfile("test", "?")))
        assert type(db) is DatabaseClient
        assert Schema.from_type(schema).tables["person"]["nickname"] == str | None
        print(db.select_from("person").select("name").compile().sql)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'select "name" from "person"'


def test_two_generated_schemas_coexist(tmp_path: Path) -> None:
    other = SCHEMA.replace("PersonTable", "UserTable").replace("person:", "user:")
    (tmp_path / "one.py").write_text(generate(SCHEMA, output="one.py"))
    (tmp_path / "two.py").write_text(generate(other, output="two.py"))
    script = textwrap.dedent(
        """
        import one, two
        from pysely import Database, Dialect
        from pysely.query_compiler import BindingProfile

        dialect = Dialect(BindingProfile("test", "?"))
        a = Database(schema=one.schema, dialect=dialect)
        b = Database(schema=two.schema, dialect=dialect)
        assert type(a) is one.DatabaseClient and type(b) is two.DatabaseClient
        assert one.DatabaseClient is not two.DatabaseClient
        print(b.select_from("user").select("name").compile().sql)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'select "name" from "user"'


class PlainPersonTable:
    id: int


class PlainSchema:
    person: PlainPersonTable


def test_database_falls_back_to_plain_client_for_ungenerated_schema() -> None:
    from pysely import Database, Dialect, Pysely
    from pysely.query_compiler import BindingProfile

    db = Database(schema=PlainSchema, dialect=Dialect(BindingProfile("test", "?")))
    assert type(db) is Pysely
    assert db.select_from("person").select("id").compile().sql == (
        'select "id" from "person"'
    )


def test_generated_module_merges_schema_typing_imports() -> None:
    source = SCHEMA.replace(
        "from typing import Literal, Optional",
        "from typing import Literal, Optional, TypedDict",
    )
    generated = generate(source)
    assert "    TypedDict," in generated
    assert generated.count("from typing import") == 1


def test_rejects_schema_class_names_the_output_defines() -> None:
    source = SCHEMA.replace("class DatabaseSchema:", "class DatabaseClient:")
    with pytest.raises(SchemaError, match="reserved.*DatabaseClient"):
        generate(source)


def test_schema_may_be_named_database() -> None:
    generated = generate(SCHEMA.replace("class DatabaseSchema:", "class Database:"))
    assert "class Database(GeneratedSchema[DatabaseClient]):" in generated
    assert "schema = Database" in generated


def test_generated_module_is_well_typed_without_its_pragma(tmp_path: Path) -> None:
    """`# mypy: ignore-errors` skips mypy's quadratic overlap check for users;
    the generator's own output must still pass mypy strict with it removed."""
    generated = generate(SCHEMA).replace(
        "# mypy: ignore-errors\n",
        '# mypy: disable-error-code="override, overload-overlap"\n',
    )
    assert "# mypy: ignore-errors" not in generated
    target = tmp_path / "schema.py"
    target.write_text(generated)
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", str(target)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={**os.environ, "MYPYPATH": str(ROOT / "src")},
    )
    assert result.returncode == 0, result.stdout


def test_heavy_overloads_live_only_under_type_checking() -> None:
    generated = generate(SCHEMA)
    typed, runtime = generated.split("\nelse:\n", 1)
    assert "if TYPE_CHECKING:" in typed
    assert "@overload" in typed
    assert "@overload" not in runtime
    assert "class DatabaseQuery(TypedSchemaQueryBuilder):" in runtime
    assert "class PersonQuery(SingleTableQuery):" in runtime
