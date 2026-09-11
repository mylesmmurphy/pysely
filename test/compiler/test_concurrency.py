from __future__ import annotations

import sys
import threading

from pysely.operation_node import (
    AndNode,
    BinaryOperationNode,
    IdentifierNode,
    SelectQueryNode,
    TableNode,
    ValueNode,
)
from pysely.query_compiler import BindingProfile, QueryCompiler

PROFILE = BindingProfile("postgres-asyncpg", "${position}")
TERMS = 40
THREADS = 8
ITERATIONS = 500


def _query(value: int) -> SelectQueryNode:
    predicates = tuple(
        BinaryOperationNode(IdentifierNode("id"), "=", ValueNode(value))
        for _ in range(TERMS)
    )
    return SelectQueryNode(
        from_=(TableNode(IdentifierNode("person")),),
        selections=(IdentifierNode("id"),),
        where=AndNode(predicates),
    )


def test_one_compiler_is_safe_across_threads() -> None:
    """A client shares a single compiler, so compiling must not share state."""
    compiler = QueryCompiler(PROFILE)
    corrupted: list[tuple[int, tuple[object, ...]]] = []
    lock = threading.Lock()
    barrier = threading.Barrier(THREADS)
    switch_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)

    def worker(value: int) -> None:
        node = _query(value)
        barrier.wait()
        for _ in range(ITERATIONS):
            compiled = compiler.compile(node, "query")
            if compiled.parameters != (value,) * TERMS:
                with lock:
                    corrupted.append((value, compiled.parameters))

    threads = [
        threading.Thread(target=worker, args=(index,)) for index in range(THREADS)
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        sys.setswitchinterval(switch_interval)

    assert not corrupted, f"{len(corrupted)} compiles picked up another thread's values"


def test_repeated_compiles_do_not_accumulate_parameters() -> None:
    compiler = QueryCompiler(PROFILE)
    node = _query(7)
    first = compiler.compile(node, "query")
    second = compiler.compile(node, "query")
    assert first.parameters == second.parameters
    assert len(second.parameters) == TERMS
