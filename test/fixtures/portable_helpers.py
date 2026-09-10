from typing import Literal, TypeVar

from test.fixtures.portable_schema import DatabaseQuery

ColumnsT = TypeVar("ColumnsT", bound=str)
KeysT = TypeVar("KeysT", bound=str)
ValuesT = TypeVar("ValuesT")


def select_pet_name(
    query: DatabaseQuery[ColumnsT, KeysT, ValuesT],
) -> DatabaseQuery[ColumnsT, KeysT | Literal["pet_name"], ValuesT | str]:
    return query.select_as("pet.name", "pet_name")
