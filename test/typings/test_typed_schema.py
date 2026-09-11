"""Stock-checker tests against the generated fixture schema.

``test/fixtures/schema.py`` is generated from ``test/fixtures/tables.py`` by
the same code path as the CLI (``test/codegen`` diffs it). Nothing here uses a
handwritten typed facade.
"""

from __future__ import annotations

import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).parents[2]
POSITIVE = ROOT / "test/typings/typed_queries.py"
NEGATIVE = ROOT / "test/typings/typed_errors.py.txt"


def pyright(path: Path) -> dict[int, list[str]]:
    """Error rules by line (1-based) from the pyright CLI."""
    result = subprocess.run(
        ["pyright", "--outputjson", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    errors: dict[int, list[str]] = {}
    for item in report["generalDiagnostics"]:
        if item["severity"] != "error":
            continue
        line = item["range"]["start"]["line"] + 1
        errors.setdefault(line, []).append(item.get("rule", item["message"]))
    return errors


def mypy(path: Path) -> dict[int, list[str]]:
    """Error codes by line (1-based) from the mypy CLI."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--no-error-summary", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "MYPYPATH": str(ROOT)},
    )
    errors: dict[int, list[str]] = {}
    for line in result.stdout.splitlines():
        match = re.match(r".*?:(\d+): error: .*\[([a-z-]+)\]$", line)
        if match:
            errors.setdefault(int(match.group(1)), []).append(match.group(2))
    return errors


def expected_error_lines(source: str) -> set[int]:
    return {
        number
        for number, line in enumerate(source.splitlines(), start=1)
        if line.rstrip().endswith("# error")
    }


def test_positive_fixture_is_clean_under_both_checkers() -> None:
    assert pyright(POSITIVE) == {}
    assert mypy(POSITIVE) == {}


@pytest.mark.parametrize("checker", [pyright, mypy])
def test_negative_fixture_errors_land_on_marked_lines(
    tmp_path: Path, checker: Any
) -> None:
    source = NEGATIVE.read_text()
    target = tmp_path / "typed_errors.py"
    target.write_text(source)
    expected = expected_error_lines(source)
    found = checker(target)
    # pyright's "No overloads" range starts at the call; every case is one line.
    assert set(found) == expected, {
        "missing": sorted(expected - set(found)),
        "unexpected": {line: found[line] for line in sorted(set(found) - expected)},
    }


def test_pyright_reports_argument_level_detail(tmp_path: Path) -> None:
    """A call-level "No overloads" error is paired with an argument-level one."""
    source = NEGATIVE.read_text()
    target = tmp_path / "typed_errors.py"
    target.write_text(source)
    lines = source.splitlines()
    errors = pyright(target)
    detailed = {"reportArgumentType", "reportAssertTypeFailure", "reportIndexIssue"}
    for number in expected_error_lines(source):
        rules = set(errors[number])
        if rules == {"reportCallIssue"}:
            code = lines[number - 1]
            pytest.fail(f"line {number} only has a call-level error: {code}")
        assert rules & detailed or "reportCallIssue" not in rules, (number, rules)


def test_pyright_only_dynamic_alias_falls_back_to_object(tmp_path: Path) -> None:
    """pyright keeps `str` off the LiteralString bound; mypy cannot (see docs)."""
    target = tmp_path / "dynamic_alias.py"
    target.write_text(
        "from typing import assert_type\n"
        "from pysely import Database\n"
        "from test.fixtures.dialects import postgres_dialect\n"
        "from test.fixtures.schema import schema\n"
        "db = Database(schema=schema, dialect=postgres_dialect())\n"
        "async def f(alias: str) -> None:\n"
        '    row = await db.select_from("person").select_as("first_name", alias)'
        ".execute_take_first_or_throw()\n"
        '    assert_type(row["anything"], object)\n'
    )
    assert pyright(target) == {}


# --- language server completions -------------------------------------------


def send(process: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    body = json.dumps(message).encode()
    assert process.stdin is not None
    process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    process.stdin.flush()


def read_exactly(process: subprocess.Popen[bytes], size: int) -> bytes:
    """Unbuffered pipes return short reads; a large response spans several."""
    assert process.stdout is not None
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = process.stdout.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def receive(process: subprocess.Popen[bytes], request_id: int) -> dict[str, Any]:
    assert process.stdout is not None
    while select.select([process.stdout], [], [], 20)[0]:
        headers: dict[str, str] = {}
        while line := process.stdout.readline().decode():
            if line == "\r\n":
                break
            name, value = line.split(":", 1)
            headers[name.lower()] = value.strip()
        response = json.loads(read_exactly(process, int(headers["content-length"])))
        if response.get("id") == request_id:
            return response
    raise AssertionError("Pyright language server did not respond")


class LanguageServer:
    def __init__(self) -> None:
        executable = shutil.which("pyright-langserver")
        assert executable is not None
        self.process = subprocess.Popen(
            [executable, "--stdio"],
            cwd=ROOT,
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.uri = (ROOT / "test/typings/lsp_sample.py").as_uri()
        self.request_id = 1
        send(
            self.process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": None,
                    "rootUri": ROOT.as_uri(),
                    "capabilities": {
                        "textDocument": {
                            "completion": {
                                "contextSupport": True,
                                "completionItem": {"snippetSupport": True},
                            }
                        }
                    },
                },
            },
        )
        assert "result" in receive(self.process, 1)
        send(self.process, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        send(
            self.process,
            {
                "jsonrpc": "2.0",
                "method": "workspace/didChangeConfiguration",
                "params": {
                    "settings": {
                        "python": {
                            "pythonPath": sys.executable,
                            "analysis": {"extraPaths": [str(ROOT), str(ROOT / "src")]},
                        }
                    }
                },
            },
        )
        self.opened = False

    def close(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)

    def completions(self, code: str) -> set[str]:
        """Completion labels at the ``""`` cursor in ``code``."""
        line = next(
            number for number, text in enumerate(code.splitlines()) if '""' in text
        )
        character = code.splitlines()[line].index('""') + 1
        self.request_id += 1
        if not self.opened:
            send(
                self.process,
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": self.uri,
                            "languageId": "python",
                            "version": 1,
                            "text": code,
                        }
                    },
                },
            )
            self.opened = True
            time.sleep(1)
        else:
            send(
                self.process,
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/didChange",
                    "params": {
                        "textDocument": {"uri": self.uri, "version": self.request_id},
                        "contentChanges": [{"text": code}],
                    },
                },
            )
            time.sleep(0.25)
        send(
            self.process,
            {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": self.uri},
                    "position": {"line": line, "character": character},
                    "context": {"triggerKind": 2, "triggerCharacter": '"'},
                },
            },
        )
        result = receive(self.process, self.request_id)["result"]
        items = cast(
            list[dict[str, Any]],
            result["items"] if isinstance(result, dict) else result,
        )
        return {item["label"].strip("\"'") for item in items}


PREFIX = (
    "from test.fixtures.dialects import postgres_dialect\n"
    "from test.fixtures.schema import schema\n"
    "from pysely import Database\n\n"
    "db = Database(schema=schema, dialect=postgres_dialect())\n"
)


@pytest.fixture(scope="module")
def server() -> Any:
    instance = LanguageServer()
    yield instance
    instance.close()


def test_completes_table_names(server: LanguageServer) -> None:
    labels = server.completions(PREFIX + 'db.select_from("")\n')
    assert {"person", "pet", "toy"} <= labels


def test_completes_columns_in_scope_only(server: LanguageServer) -> None:
    before = server.completions(
        PREFIX + 'query = db.select_from("person")\nquery.where("", "=", 1)\n'
    )
    assert {"person.id", "person.first_name", "first_name", "id"} <= before
    assert "species" not in before
    assert "pet.name" not in before

    after = server.completions(
        PREFIX + 'query = db.select_from("person")\n'
        'joined = query.inner_join("pet", "person.id", "pet.owner_id")\n'
        'joined.where("", "=", "dog")\n'
    )
    assert {"person.id", "pet.name", "species", "first_name"} <= after
    # `id` is ambiguous once two owners are in scope, so it is not offered.
    assert "id" not in after
    assert "toy.name" not in after


def test_completes_columns_inside_callbacks(server: LanguageServer) -> None:
    labels = server.completions(
        PREFIX + 'query = db.select_from("person")\n'
        'joined = query.inner_join("pet", "person.id", "pet.owner_id")\n'
        'joined.where(lambda eb: eb("", "=", "dog"))\n'
    )
    assert {"person.id", "pet.name", "species"} <= labels


def test_completes_result_keys(server: LanguageServer) -> None:
    code = PREFIX + (
        'query = db.select_from("person")\n'
        'joined = query.inner_join("pet", "person.id", "pet.owner_id")\n'
        'selected = joined.select("first_name").select_as("pet.name", "pet_name")\n'
        "async def inspect() -> None:\n"
        "    row = await selected.execute_take_first_or_throw()\n"
        '    row[""]\n'
    )
    labels = server.completions(code)
    assert {"first_name", "pet_name"} <= labels
    assert "species" not in labels

    dropped = code.replace('.select_as("pet.name", "pet_name")', "")
    labels = server.completions(dropped)
    assert "first_name" in labels
    assert "pet_name" not in labels


def test_value_completions_after_a_join_are_a_superset(
    server: LanguageServer,
) -> None:
    """Documented upstream behaviour: pyright unions the value literals of every
    overload whose receiver matches, so the pet enum appears at a person column."""
    labels = server.completions(
        PREFIX + 'query = db.select_from("person")\n'
        'joined = query.inner_join("pet", "person.id", "pet.owner_id")\n'
        'joined.where("status", "=", "")\n'
    )
    assert {"active", "inactive"} <= labels
    assert {"cat", "dog", "hamster"} <= labels  # the superset
    single = server.completions(
        PREFIX + 'query = db.select_from("person")\nquery.where("status", "=", "")\n'
    )
    assert {"active", "inactive"} <= single
    assert "dog" not in single
