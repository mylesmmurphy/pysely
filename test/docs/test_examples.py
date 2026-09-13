"""Keep the copyable documentation examples connected to the real API."""

from __future__ import annotations

import ast
import inspect
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import aiosqlite
import pytest

from pysely import SqliteDialect
from pysely.schema_definition import QueryCore
from pysely.typgen import generate
from test.fixtures.schema import DatabaseSchema

ROOT = Path(__file__).parents[2]


def python_blocks(page: Path) -> list[str]:
    return [
        textwrap.dedent(match)
        for match in re.findall(
            r"^[ \t]*```python\n(.*?)^[ \t]*```", page.read_text(), re.M | re.S
        )
    ]


@pytest.mark.parametrize("page", sorted((ROOT / "docs").rglob("*.md")))
def test_documentation_python_syntax(page: Path) -> None:
    for block in python_blocks(page):
        compile(block, str(page), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)


def test_quickstart_runs_verbatim(tmp_path: Path) -> None:
    schema, application = python_blocks(ROOT / "docs/getting-started.md")
    (tmp_path / "dbschema.py").write_text(schema)
    (tmp_path / "db.py").write_text(application)
    generated = subprocess.run(
        [sys.executable, "-m", "pysely.cli", "typgen", "dbschema.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert generated.returncode == 0, generated.stderr
    result = subprocess.run(
        [sys.executable, "db.py"], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "{'id': 1, 'first_name': 'Ada'}"

    # Deploying without the generated stub must preserve runtime behavior.
    (tmp_path / "dbschema.pyi").unlink()
    without_stub = subprocess.run(
        [sys.executable, "db.py"], cwd=tmp_path, capture_output=True, text=True
    )
    assert without_stub.returncode == 0, without_stub.stderr
    assert without_stub.stdout == result.stdout


@pytest.mark.parametrize("checker", ["mypy", "pyright"])
def test_quickstart_and_helper_types(tmp_path: Path, checker: str) -> None:
    schema, application = python_blocks(ROOT / "docs/getting-started.md")
    helper = python_blocks(ROOT / "docs/typing.md")[-1]
    (tmp_path / "dbschema.py").write_text(schema)
    (tmp_path / "dbschema.pyi").write_text(generate(schema))
    (tmp_path / "db.py").write_text(application)
    (tmp_path / "helper.py").write_text(helper)
    if checker == "mypy":
        arguments = ["--strict", "db.py", "helper.py"]
    else:
        (tmp_path / "pyrightconfig.json").write_text(
            json.dumps(
                {"typeCheckingMode": "strict", "include": ["db.py", "helper.py"]}
            )
        )
        arguments = ["--pythonpath", sys.executable]
    result = subprocess.run(
        [sys.executable, "-m", checker, *arguments],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.asyncio
async def test_query_reference_examples_execute() -> None:
    database = await aiosqlite.connect(":memory:", isolation_level=None)
    async with DatabaseSchema.connect(dialect=SqliteDialect(database=database)) as db:
        await database.executescript(
            """
            create table person (
                id integer primary key, first_name text not null,
                last_name text, status text not null
            );
            create table pet (
                id integer primary key, owner_id integer not null,
                name text not null, species text not null
            );
            insert into person values (1, 'Ada', NULL, 'active');
            insert into pet values (1, 1, 'Milo', 'cat');
            """
        )
        namespace: dict[str, object] = {"db": db}
        page = ROOT / "docs/queries.md"
        for block in python_blocks(page):
            code = compile(
                block, str(page), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
            )
            result = eval(code, namespace)
            if inspect.isawaitable(result):
                await result
            # Also exercise snippets which only construct a query.
            for name in ("query", "names"):
                query = namespace.get(name)
                if isinstance(query, QueryCore):
                    await query.execute()
