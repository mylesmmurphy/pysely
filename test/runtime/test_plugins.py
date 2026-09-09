from __future__ import annotations

from dataclasses import replace

from pysely import Pysely, QueryPlugin
from pysely.driver import QueryResult
from pysely.operation_node import RootOperationNode
from test.runtime.test_sqlite_execution import create_database, sqlite_dialect, users


class RecordingPlugin(QueryPlugin):
    def __init__(self, name: str, events: list[str]) -> None:
        self._name = name
        self._events = events

    def transform_query(
        self, query: RootOperationNode, query_id: str
    ) -> RootOperationNode:
        self._events.append(f"query:{self._name}")
        return query

    def transform_result(
        self, result: QueryResult[dict[str, object]], query_id: str
    ) -> QueryResult[dict[str, object]]:
        self._events.append(f"result:{self._name}")
        rows = tuple({**row, self._name: True} for row in result.rows)
        return replace(result, rows=rows)


async def test_plugins_transform_queries_and_results_in_registration_order(
    tmp_path,
) -> None:
    database = str(tmp_path / "pysely.db")
    await create_database(database)
    events: list[str] = []
    plugins = (
        RecordingPlugin("first", events),
        RecordingPlugin("second", events),
    )

    async with Pysely[object](dialect=sqlite_dialect(database), plugins=plugins) as db:
        rows = await db.select_from(users).select(users.c.id).execute()

    assert events == ["query:first", "query:second", "result:first", "result:second"]
    assert rows == [
        {"id": 1, "first": True, "second": True},
        {"id": 2, "first": True, "second": True},
    ]
