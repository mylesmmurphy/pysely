"""Command line entry point for Pysely."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from pysely.typgen import SchemaError, generate


def _typgen(arguments: argparse.Namespace) -> int:
    schema: Path = arguments.schema
    output: Path = arguments.output or schema.with_suffix(".pyi")
    if (
        schema.suffix != ".py"
        or output.resolve() != schema.with_suffix(".pyi").resolve()
    ):
        print(
            "pysely: output must be the adjacent .pyi for the input .py schema",
            file=sys.stderr,
        )
        return 2
    try:
        source = schema.read_text()
    except OSError as error:
        print(f"pysely: cannot read {schema}: {error}", file=sys.stderr)
        return 2
    try:
        generated = generate(source, source_name=str(schema), output=str(output))
    except (SchemaError, SyntaxError) as error:
        print(f"pysely: {schema}: {error}", file=sys.stderr)
        return 2

    if arguments.check:
        current = output.read_text() if output.exists() else None
        if current == generated:
            return 0
        reason = "is out of date" if current is not None else "does not exist"
        print(
            f"pysely: {output} {reason}; run `pysely typgen "
            f"{schema} --output {output}`",
            file=sys.stderr,
        )
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated)
    print(f"pysely: wrote {output}")
    return 0


def _introspect(arguments: argparse.Namespace) -> int:
    from pysely.introspect import (
        MAPPINGS,
        introspect_mysql,
        introspect_postgres,
        introspect_sqlite,
        parse_overrides,
        render_tables,
    )

    output: Path = arguments.output
    try:
        overrides = parse_overrides(arguments.override)
        if arguments.dialect == "sqlite":
            tables = introspect_sqlite(arguments.url)
        elif arguments.dialect == "postgres":
            tables = asyncio.run(introspect_postgres(arguments.url, arguments.schema))
        else:
            tables = asyncio.run(
                introspect_mysql(arguments.schema, **_mysql_options(arguments.url))
            )
        source = render_tables(
            tables,
            MAPPINGS[arguments.dialect],
            dialect=arguments.dialect,
            overrides=overrides,
            unknown=arguments.unknown,
        )
    except SchemaError as error:
        print(f"pysely: {error}", file=sys.stderr)
        return 2
    except ImportError as error:
        print(f"pysely: {error}; install pysely[{arguments.dialect}]", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source)
    print(f"pysely: wrote {output} ({len(tables)} tables)")
    return 0


def _mysql_options(url: str) -> dict[str, object]:
    """``mysql://user:password@host:port`` -> asyncmy connect keywords."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    options: dict[str, object] = {}
    if parts.hostname:
        options["host"] = parts.hostname
    if parts.port:
        options["port"] = parts.port
    if parts.username:
        options["user"] = parts.username
    if parts.password:
        options["password"] = parts.password
    return options


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pysely")
    commands = parser.add_subparsers(dest="command", required=True)
    typgen = commands.add_parser(
        "typgen",
        help="write an adjacent type stub for a handwritten schema",
    )
    typgen.add_argument("schema", type=Path, help="module containing table classes")
    typgen.add_argument(
        "-o",
        "--output",
        type=Path,
        help="adjacent .pyi output (defaults to the schema path with .pyi suffix)",
    )
    typgen.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the output is missing or out of date",
    )
    introspect = commands.add_parser(
        "introspect",
        help="write annotated table classes from a live database",
    )
    introspect.add_argument(
        "--dialect", choices=["sqlite", "postgres", "mysql"], required=True
    )
    introspect.add_argument(
        "--url",
        required=True,
        help="SQLite file path, PostgreSQL DSN, or mysql://user:pass@host:port",
    )
    introspect.add_argument(
        "--schema",
        default="public",
        help="PostgreSQL schema or MySQL database to read (default: public)",
    )
    introspect.add_argument(
        "-o", "--output", type=Path, required=True, help="tables module to write"
    )
    introspect.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="TABLE.COLUMN=TYPE",
        help="annotation to use for a column instead of the mapped type",
    )
    introspect.add_argument(
        "--unknown",
        choices=["fail", "object"],
        default="fail",
        help="what to do with a SQL type that has no Python mapping",
    )
    arguments = parser.parse_args(argv)
    if arguments.command == "typgen":
        return _typgen(arguments)
    if arguments.command == "introspect":
        return _introspect(arguments)
    parser.error(f"unknown command: {arguments.command}")  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
