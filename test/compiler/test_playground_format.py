import json
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from pysely.codegen import generate


def test_playground_formats_compiled_sql_by_clause() -> None:
    namespace = runpy.run_path("docs/assets/playground.py")
    format_sql = cast(Callable[[str], str], namespace["format_sql"])

    assert format_sql(
        'select "first_name", "pet"."name" as "pet_name" from "person" '
        'inner join "pet" on "owner_id" = "person"."id" '
        'where ("first_name" = $1 and "species" = $2)'
    ) == (
        'select "first_name", "pet"."name" as "pet_name"\n'
        'from "person"\n'
        'inner join "pet" on "owner_id" = "person"."id"\n'
        'where ("first_name" = $1 and "species" = $2)'
    )


def test_playground_compiles_example_with_each_dialect() -> None:
    namespace = runpy.run_path("docs/assets/playground.py")
    evaluate = cast(Callable[[str, str, str], str], namespace["evaluate_playground"])
    example_dir = Path("docs/assets/examples")
    schema = (example_dir / "schema.py").read_text()
    query = (example_dir / "query.py").read_text()

    for dialect in ("postgres", "mysql", "sqlite"):
        result = cast(dict[str, Any], json.loads(evaluate(schema, query, dialect)))
        assert "error" not in result
        assert "pet_name" in result["sql"]
        assert result["database"] == generate(schema, output="database.py")


def test_playground_regenerates_the_interface_from_the_schema_editor() -> None:
    """A column added in the schema editor must work without a rebuild."""
    namespace = runpy.run_path("docs/assets/playground.py")
    evaluate = cast(Callable[[str, str, str], str], namespace["evaluate_playground"])
    schema = (Path("docs/assets/examples") / "schema.py").read_text()
    edited = schema.replace(
        "    last_name: str | None\n",
        "    last_name: str | None\n    nickname: str | None\n",
    )
    query = (
        "from database import DatabaseSchema\n"
        "from playground import dialect\n"
        "from pysely import Pysely\n"
        "db = Pysely.create(schema=DatabaseSchema, dialect=dialect)\n"
        'compiled = db.select_from("person").select("nickname").compile()\n'
    )

    result = cast(dict[str, Any], json.loads(evaluate(edited, query, "postgres")))

    assert "error" not in result
    assert result["sql"] == 'select "nickname"\nfrom "person"'
    assert '"person.nickname",' in result["database"]


def test_playground_dialect_is_compilation_only() -> None:
    namespace = runpy.run_path("docs/assets/playground.py")
    dialect = namespace["compilation_dialect"]("postgres")

    assert dialect.driver is None
