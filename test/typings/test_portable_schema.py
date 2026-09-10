import json
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[2]


def send(process: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    body = json.dumps(message).encode()
    assert process.stdin is not None
    process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
    process.stdin.flush()


def receive(process: subprocess.Popen[bytes], request_id: int) -> dict[str, Any]:
    assert process.stdout is not None
    while select.select([process.stdout], [], [], 20)[0]:
        headers: dict[str, str] = {}
        while line := process.stdout.readline().decode():
            if line == "\r\n":
                break
            name, value = line.split(":", 1)
            headers[name.lower()] = value.strip()
        response = json.loads(process.stdout.read(int(headers["content-length"])))
        if response.get("id") == request_id:
            return response
    raise AssertionError("Pyright language server did not respond")


def completion_labels(
    process: subprocess.Popen[bytes], request_id: int, code: str, line: int
) -> set[str]:
    uri = (ROOT / "test/typings/lsp_sample.py").as_uri()
    character = code.splitlines()[line].index('""') + 1
    send(
        process,
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": uri, "version": request_id},
                "contentChanges": [{"text": code}],
            },
        },
    )
    time.sleep(0.25)
    send(
        process,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "textDocument/completion",
            "params": {
                "textDocument": {"uri": uri},
                "position": {
                    "line": line,
                    "character": character,
                },
                "context": {"triggerKind": 2, "triggerCharacter": '"'},
            },
        },
    )
    result = receive(process, request_id)["result"]
    items = cast(
        list[dict[str, Any]],
        result["items"] if isinstance(result, dict) else result,
    )
    return {item["label"].strip("\"'") for item in items}


def test_pyright_language_server_completes_generated_schema() -> None:
    executable = shutil.which("pyright-langserver")
    assert executable is not None
    process = subprocess.Popen(
        [executable, "--stdio"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    uri = (ROOT / "test/typings/lsp_sample.py").as_uri()
    try:
        send(
            process,
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
                                "completionItem": {
                                    "snippetSupport": True,
                                    "documentationFormat": [
                                        "markdown",
                                        "plaintext",
                                    ],
                                },
                            }
                        }
                    },
                },
            },
        )
        assert "result" in receive(process, 1)
        send(process, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        send(
            process,
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

        prefix = (
            "from test.fixtures.dialects import postgres_dialect\n"
            "from test.fixtures.portable_schema import Database\n\n"
            "db = Database(dialect=postgres_dialect())\n"
        )
        code = prefix + 'db.select_from("")\n'
        send(
            process,
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": uri,
                        "languageId": "python",
                        "version": 1,
                        "text": code,
                    }
                },
            },
        )
        time.sleep(1)
        assert {"person", "pet"} <= completion_labels(process, 2, code, 4)

        code = prefix + 'query = db.select_from("person")\nquery.where("", "=", 1)\n'
        before_join = completion_labels(process, 3, code, 5)
        assert {"person.id", "person.first_name", "first_name"} <= before_join
        assert "species" not in before_join

        code = prefix + (
            'query = db.select_from("person")\n'
            'joined = query.inner_join("pet", "person.id", "pet.owner_id")\n'
            'joined.where("", "=", "dog")\n'
        )
        after_join = completion_labels(process, 4, code, 6)
        assert {"person.id", "pet.name", "species"} <= after_join

        code = prefix + (
            'query = db.select_from("person")\n'
            'joined = query.inner_join("pet", "person.id", "pet.owner_id")\n'
            'selected = joined.select_as("pet.name", "pet_name")\n'
            "async def inspect() -> None:\n"
            "    row = await selected.execute_take_first_or_throw()\n"
            '    row[""]\n'
        )
        result_line = code.splitlines().index('    row[""]')
        result_keys = completion_labels(process, 5, code, result_line)
        assert "pet_name" in result_keys
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_pyright_rejects_columns_outside_generated_scope(tmp_path: Path) -> None:
    source = tmp_path / "portable_schema_errors.py"
    source.write_text((ROOT / "test/typings/portable_schema_errors.txt").read_text())
    result = subprocess.run(
        ["pyright", str(source)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stdout.count("reportArgumentType") == 3
