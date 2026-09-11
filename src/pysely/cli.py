"""Command line entry point for Pysely."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pysely.codegen import SchemaError, generate


def _codegen(arguments: argparse.Namespace) -> int:
    schema: Path = arguments.schema
    output: Path = arguments.output
    try:
        source = schema.read_text()
    except OSError as error:
        print(f"pysely: cannot read {schema}: {error}", file=sys.stderr)
        return 2
    try:
        generated = generate(source, source_name=schema.name, output=str(output))
    except (SchemaError, SyntaxError) as error:
        print(f"pysely: {schema}: {error}", file=sys.stderr)
        return 2

    if arguments.check:
        current = output.read_text() if output.exists() else None
        if current == generated:
            return 0
        reason = "is out of date" if current is not None else "does not exist"
        print(
            f"pysely: {output} {reason}; run `pysely codegen "
            f"{schema} --output {output}`",
            file=sys.stderr,
        )
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated)
    print(f"pysely: wrote {output}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pysely")
    commands = parser.add_subparsers(dest="command", required=True)
    codegen = commands.add_parser(
        "codegen",
        help="generate a typed query interface from annotated schema classes",
    )
    codegen.add_argument("schema", type=Path, help="module containing schema classes")
    codegen.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="file to write the generated interface to",
    )
    codegen.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the output is missing or out of date",
    )
    arguments = parser.parse_args(argv)
    if arguments.command == "codegen":
        return _codegen(arguments)
    parser.error(f"unknown command: {arguments.command}")  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
