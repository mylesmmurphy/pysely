from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--dialect",
        choices=("postgres", "mysql", "sqlite", "mssql", "pglite"),
    )


def require_service(pytestconfig: pytest.Config, dialect: str, variable: str) -> str:
    value = os.getenv(variable)
    if value:
        return value
    if pytestconfig.getoption("--dialect") == dialect:
        pytest.fail(f"{variable} is required for the {dialect} test job")
    pytest.skip(f"{dialect} service is not configured")
