import json
import sys
import traceback
import types

from pysely import Dialect
from pysely.codegen import generate
from pysely.query_compiler import BindingProfile

SQL_CLAUSES = (
    "delete from",
    "insert into",
    "inner join",
    "left join",
    "right join",
    "full join",
    "group by",
    "order by",
    "returning",
    "select",
    "update",
    "values",
    "from",
    "where",
    "having",
    "limit",
    "offset",
    "output",
    "set",
)


def format_sql(sql):
    breaks = []
    quote = None
    depth = 0
    index = 0

    while index < len(sql):
        character = sql[index]
        if quote:
            if character == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if character in {'"', "'", "`"}:
            quote = character
            index += 1
            continue
        if character == "[":
            quote = "]"
            index += 1
            continue
        if character == "(":
            depth += 1
            index += 1
            continue
        if character == ")":
            depth -= 1
            index += 1
            continue
        if depth == 0:
            lower = sql[index:].lower()
            for clause in SQL_CLAUSES:
                if not lower.startswith(clause):
                    continue
                before = sql[index - 1] if index else " "
                after_index = index + len(clause)
                after = sql[after_index] if after_index < len(sql) else " "
                if not before.isalnum() and not after.isalnum() and after != "_":
                    breaks.append((index, after_index, clause))
                    index = after_index
                    break
            else:
                index += 1
            continue
        index += 1

    if not breaks:
        return sql

    lines = []
    for position, (_, end, clause) in enumerate(breaks):
        next_start = breaks[position + 1][0] if position + 1 < len(breaks) else len(sql)
        body = sql[end:next_start].strip()
        lines.append(f"{clause} {body}".rstrip())
    return "\n".join(lines)


PROFILES = {
    "postgres": BindingProfile("postgres-asyncpg", "${position}"),
    "mysql": BindingProfile("mysql-asyncmy", "%s", "`", "`", None),
    "sqlite": BindingProfile("sqlite-aiosqlite", "?"),
}


def compilation_dialect(name):
    return Dialect(PROFILES[name])


def evaluate_playground(tables_code, query_code, dialect_name):
    schema_code = ""
    try:
        # Exactly what `pysely codegen` writes for these tables. The playground
        # runs the real generator so the typed schema always matches the
        # tables editor rather than a file baked in at build time.
        schema_code = generate(tables_code, output="schema.py")
        schema = types.ModuleType("schema")
        sys.modules["schema"] = schema
        exec(compile(schema_code, "schema.py", "exec"), schema.__dict__)
        environment = types.ModuleType("playground")
        environment.dialect = compilation_dialect(dialect_name)
        sys.modules["playground"] = environment
        namespace = {}
        exec(compile(query_code, "query.py", "exec"), namespace)
        compiled = namespace["compiled"]
        return json.dumps(
            {
                "sql": format_sql(compiled.sql),
                "parameters": compiled.parameters,
                "schema": schema_code,
            },
            default=str,
        )
    except Exception as error:
        frames = traceback.extract_tb(error.__traceback__)
        frame = next(
            (
                frame
                for frame in reversed(frames)
                if frame.filename in {"tables.py", "schema.py", "query.py"}
            ),
            None,
        )
        return json.dumps(
            {
                "error": str(error),
                "file": getattr(error, "filename", None)
                or (frame.filename if frame else "query.py"),
                "line": getattr(error, "lineno", None)
                or (frame.lineno if frame else 1),
                "schema": schema_code,
            }
        )
