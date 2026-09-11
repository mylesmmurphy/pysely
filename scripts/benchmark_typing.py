"""Measure how generated modules scale for the checkers and the editor.

Builds synthetic schemas (shared column names, 10-30 columns per table),
generates them with the real generator, and records generated size,
generation time, cold and warm checker time, Pyright RSS, and warm completion
latency from the stock Pyright language server.

    uv run python scripts/benchmark_typing.py --tables 20 100 300
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import select
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from pysely.codegen import generate

ROOT = Path(__file__).parents[1]
SHARED = ["id", "name", "created_at", "updated_at", "status", "owner_id"]
TYPES = [
    "int",
    "str",
    "str | None",
    "bool",
    "float",
    "datetime",
    "date | None",
    "Decimal",
    'Literal["draft", "live", "archived"]',
]


def synthetic_schema(tables: int) -> str:
    lines = [
        "from datetime import date, datetime",
        "from decimal import Decimal",
        "from typing import Literal",
        "",
        "",
    ]
    for index in range(tables):
        columns = 10 + (index * 7) % 21  # 10..30
        lines.append(f"class Table{index}:")
        for column in range(columns):
            if column < len(SHARED):
                name = SHARED[column]
                annotation = ["int", "str", "datetime", "datetime", TYPES[8], "int"][
                    column
                ]
            else:
                name = f"field_{column}"
                annotation = TYPES[(index + column) % len(TYPES)]
            lines.append(f"    {name}: {annotation}")
        lines.append("")
        lines.append("")
    lines.append("class DatabaseSchema:")
    lines += [f"    t{index}: Table{index}" for index in range(tables)]
    lines.append("")
    return "\n".join(lines)


def queries(tables: int) -> dict[str, str]:
    """Representative editor buffers; `""` marks the completion cursor."""
    prefix = (
        "from schema import schema\n"
        "from pysely import Database, Dialect\n"
        "from pysely.query_compiler import BindingProfile\n\n"
        'db = Database(schema=schema, dialect=Dialect(BindingProfile("b", "?")))\n'
    )
    last = tables - 1
    single = prefix + 'q = db.select_from("t0").select("")\n'
    joined = prefix + (
        'q = db.select_from("t0").inner_join("t1", "t1.owner_id", "t0.id")'
        '.where("t1.status", "=", "live").select("")\n'
    )
    three = prefix + (
        'q = db.select_from("t0").inner_join("t1", "t1.owner_id", "t0.id")'
        f'.left_join("t{last}", "t{last}.owner_id", "t1.id")'
        '.where("t1.status", "=", "live").where("t0.owner_id", "=", 1)'
        '.select("t0.name").select("t1.field_8").select("")\n'
    )
    return {"single": single, "join2": joined, "join3": three}


def projection_query(width: int) -> str:
    """A chained projection of ``width`` columns, checked by the CLI."""
    # t0 has ten columns; wide projections alias them to keep keys distinct.
    selects = "".join(
        f'.select_as("t0.field_{column % 4 + 6}", "c{column}")'
        for column in range(width)
    )
    return (
        "from schema import schema\n"
        "from pysely import Database, Dialect\n"
        "from pysely.query_compiler import BindingProfile\n\n"
        'db = Database(schema=schema, dialect=Dialect(BindingProfile("b", "?")))\n'
        f'q = db.select_from("t0"){selects}\n'
        "async def main() -> None:\n"
        "    row = await q.execute_take_first_or_throw()\n"
        '    reveal_type(row["c0"])\n'
    )


def timed(
    command: list[str], cwd: Path, env: dict[str, str] | None = None
) -> tuple[float, int, int]:
    """(seconds, exit code, max RSS in MB) for one subprocess."""
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    start = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=env)
    elapsed = time.perf_counter() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    scale = 1024 * 1024 if sys.platform == "darwin" else 1024
    return elapsed, result.returncode, max(after - before, 0) // scale or after // scale


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


class LanguageServer:
    def __init__(self, root: Path) -> None:
        executable = shutil.which("pyright-langserver")
        assert executable, "pyright-langserver is not installed"
        self.process = subprocess.Popen(
            [executable, "--stdio"],
            cwd=root,
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.root = root
        self.uri = (root / "buffer.py").as_uri()
        self.next_id = 0
        self.request(
            "initialize",
            {"processId": None, "rootUri": root.as_uri(), "capabilities": {}},
        )
        self.notify("initialized", {})
        self.notify(
            "workspace/didChangeConfiguration",
            {
                "settings": {
                    "python": {
                        "pythonPath": sys.executable,
                        "analysis": {"extraPaths": [str(root), str(ROOT / "src")]},
                    }
                }
            },
        )
        self.version = 0
        self.opened = False

    def send(self, message: dict[str, Any]) -> None:
        body = json.dumps(message).encode()
        assert self.process.stdin
        self.process.stdin.write(f"Content-Length: {len(body)}\r\n\r\n".encode() + body)
        self.process.stdin.flush()

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.next_id += 1
        self.send(
            {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}
        )
        assert self.process.stdout
        while select.select([self.process.stdout], [], [], 120)[0]:
            headers: dict[str, str] = {}
            while line := self.process.stdout.readline().decode():
                if line == "\r\n":
                    break
                name, value = line.split(":", 1)
                headers[name.lower()] = value.strip()
            response = json.loads(
                read_exactly(self.process, int(headers["content-length"]))
            )
            if response.get("id") == self.next_id:
                return response
        raise RuntimeError("language server timed out")

    def set_text(self, text: str) -> None:
        self.version += 1
        if not self.opened:
            self.notify(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": self.uri,
                        "languageId": "python",
                        "version": 1,
                        "text": text,
                    }
                },
            )
            self.opened = True
        else:
            self.notify(
                "textDocument/didChange",
                {
                    "textDocument": {"uri": self.uri, "version": self.version},
                    "contentChanges": [{"text": text}],
                },
            )

    def completion(self, text: str) -> tuple[float, int]:
        """Milliseconds and item count for a completion at the `""` cursor."""
        self.set_text(text)
        line = next(
            number for number, item in enumerate(text.splitlines()) if '""' in item
        )
        character = text.splitlines()[line].index('""') + 1
        start = time.perf_counter()
        response = self.request(
            "textDocument/completion",
            {
                "textDocument": {"uri": self.uri},
                "position": {"line": line, "character": character},
                "context": {"triggerKind": 2, "triggerCharacter": '"'},
            },
        )
        elapsed = (time.perf_counter() - start) * 1000
        result = response.get("result") or {}
        items = result["items"] if isinstance(result, dict) else result
        return elapsed, len(items)

    def close(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)


def benchmark(tables: int, rounds: int) -> dict[str, Any]:
    workdir = Path(tempfile.mkdtemp(prefix=f"pysely-bench-{tables}-"))
    (workdir / "tables.py").write_text(synthetic_schema(tables))
    start = time.perf_counter()
    generated = generate((workdir / "tables.py").read_text(), output="schema.py")
    generation = time.perf_counter() - start
    (workdir / "schema.py").write_text(generated)
    (workdir / "pyrightconfig.json").write_text(
        json.dumps({"extraPaths": [str(ROOT / "src")], "typeCheckingMode": "standard"})
    )
    result: dict[str, Any] = {
        "tables": tables,
        "columns": sum(10 + (index * 7) % 21 for index in range(tables)),
        "generated_bytes": len(generated.encode()),
        "generated_lines": generated.count("\n"),
        "overloads": generated.count("@overload"),
        "generation_seconds": round(generation, 3),
    }
    for width in (5, 20, 50):
        (workdir / f"projection_{width}.py").write_text(projection_query(width))
    buffers = queries(tables)
    for name, text in buffers.items():
        (workdir / f"{name}.py").write_text(text.replace('""', '"t0.name"'))

    checks = [str(workdir / f"{name}.py") for name in buffers] + [
        str(workdir / f"projection_{width}.py") for width in (5, 20, 50)
    ]
    cold, code, rss = timed(["pyright", "--outputjson", *checks], workdir)
    warm, _, _ = timed(["pyright", "--outputjson", *checks], workdir)
    result["pyright_cold_seconds"] = round(cold, 2)
    result["pyright_warm_seconds"] = round(warm, 2)
    result["pyright_exit"] = code
    result["pyright_max_rss_mb"] = rss
    mypy_cold, mypy_code, _ = timed(
        [sys.executable, "-m", "mypy", "--strict", *checks],
        workdir,
        env={"MYPYPATH": f"{workdir}:{ROOT / 'src'}", "PATH": "/usr/bin:/bin"},
    )
    mypy_warm, _, _ = timed(
        [sys.executable, "-m", "mypy", "--strict", *checks],
        workdir,
        env={"MYPYPATH": f"{workdir}:{ROOT / 'src'}", "PATH": "/usr/bin:/bin"},
    )
    result["mypy_cold_seconds"] = round(mypy_cold, 2)
    result["mypy_warm_seconds"] = round(mypy_warm, 2)
    result["mypy_exit"] = mypy_code

    server = LanguageServer(workdir)
    try:
        server.completion(buffers["single"])  # warm up: parse schema.py once
        latencies: dict[str, list[float]] = {name: [] for name in buffers}
        counts: dict[str, int] = {}
        for _ in range(rounds):
            for name, text in buffers.items():
                elapsed, count = server.completion(text)
                latencies[name].append(elapsed)
                counts[name] = count
        result["completion_ms"] = {
            name: {
                "p50": round(statistics.median(values)),
                "p95": round(sorted(values)[max(0, int(len(values) * 0.95) - 1)]),
                "items": counts[name],
            }
            for name, values in latencies.items()
        }
    finally:
        server.close()
    shutil.rmtree(workdir, ignore_errors=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tables", type=int, nargs="+", default=[20, 100, 300])
    parser.add_argument("--rounds", type=int, default=10)
    arguments = parser.parse_args()
    pyright = subprocess.run(
        ["pyright", "--version"], capture_output=True, text=True
    ).stdout.strip()
    mypy = subprocess.run(
        [sys.executable, "-m", "mypy", "--version"], capture_output=True, text=True
    ).stdout.strip()
    print(
        json.dumps(
            {
                "machine": platform.platform(),
                "processor": platform.processor(),
                "python": platform.python_version(),
                "pyright": pyright,
                "mypy": mypy,
            }
        )
    )
    for tables in arguments.tables:
        print(json.dumps(benchmark(tables, arguments.rounds)), flush=True)


if __name__ == "__main__":
    main()
