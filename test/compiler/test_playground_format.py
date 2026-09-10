import json
import runpy
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast


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
    evaluate = cast(
        Callable[[str, str, str, str], str], namespace["evaluate_playground"]
    )
    example_dir = Path("docs/assets/examples")
    schema = (example_dir / "schema.py").read_text()
    database = (example_dir / "database.py").read_text()
    query = (example_dir / "query.py").read_text()

    for dialect in ("postgres", "mysql", "sqlite"):
        result = cast(
            dict[str, Any], json.loads(evaluate(schema, database, query, dialect))
        )
        assert "error" not in result
        assert "pet_name" in result["sql"]


def test_playground_dialect_is_compilation_only() -> None:
    namespace = runpy.run_path("docs/assets/playground.py")
    dialect = namespace["compilation_dialect"]("postgres")

    assert dialect.driver is None
