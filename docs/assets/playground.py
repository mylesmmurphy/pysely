import json
import sys
import traceback
import types
from typing import get_type_hints

from pysely import MysqlDialect, PostgresDialect, SqliteDialect


async def unavailable_database():
    raise RuntimeError("The playground compiles queries without a database")


def evaluate_playground(schema_code, query_code, dialect_name):
    tables = {}
    try:
        schema = types.ModuleType("schema")
        sys.modules["schema"] = schema
        exec(compile(schema_code, "schema.py", "exec"), schema.__dict__)
        tables = {
            name: {column: str(kind) for column, kind in get_type_hints(row).items()}
            for name, row in get_type_hints(schema.Database).items()
        }
        dialects = {
            "postgres": PostgresDialect(pool=unavailable_database),
            "mysql": MysqlDialect(pool=unavailable_database),
            "sqlite": SqliteDialect(database=unavailable_database),
        }
        namespace = {"dialect": dialects[dialect_name]}
        exec(compile(query_code, "query.py", "exec"), namespace)
        compiled = namespace["compiled"]
        return json.dumps(
            {"tables": tables, "sql": compiled.sql, "parameters": compiled.parameters},
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
                "tables": tables,
                "error": str(error),
                "file": getattr(error, "filename", None)
                or (frame.filename if frame else "query.py"),
                "line": getattr(error, "lineno", None)
                or (frame.lineno if frame else 1),
            }
        )
