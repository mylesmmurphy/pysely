import runpy
from collections.abc import Callable
from typing import cast


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
