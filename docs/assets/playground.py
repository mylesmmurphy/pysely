import json
import sys
import traceback
import types

from pysely import MysqlDialect, PostgresDialect, SqliteDialect

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


async def unavailable_database():
    raise RuntimeError("The playground compiles queries without a database")


def evaluate_playground(schema_code, database_code, query_code, dialect_name):
    try:
        schema = types.ModuleType("schema")
        sys.modules["schema"] = schema
        exec(compile(schema_code, "schema.py", "exec"), schema.__dict__)
        database = types.ModuleType("database")
        sys.modules["database"] = database
        exec(compile(database_code, "database.py", "exec"), database.__dict__)
        dialects = {
            "postgres": PostgresDialect(pool=unavailable_database),
            "mysql": MysqlDialect(pool=unavailable_database),
            "sqlite": SqliteDialect(database=unavailable_database),
        }
        namespace = {"dialect": dialects[dialect_name]}
        exec(compile(query_code, "query.py", "exec"), namespace)
        compiled = namespace["compiled"]
        return json.dumps(
            {
                "sql": format_sql(compiled.sql),
                "parameters": compiled.parameters,
            },
            default=str,
        )
    except Exception as error:
        frames = traceback.extract_tb(error.__traceback__)
        frame = next(
            (
                frame
                for frame in reversed(frames)
                if frame.filename in {"schema.py", "query.py"}
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
            }
        )
