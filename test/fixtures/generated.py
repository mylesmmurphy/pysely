from typing import Literal, Never, NotRequired, TypedDict

from pysely import Column, Table


class UserRow(TypedDict):
    id: int
    email: str
    nickname: str | None


class UserInsert(TypedDict):
    email: str
    nickname: NotRequired[str | None]


class UserUpdate(TypedDict, total=False):
    email: str
    nickname: str | None


class UsersColumns:
    id: Column[int, Never, Never, Literal["id"], str]
    email: Column[str, str, str, Literal["email"], str]
    nickname: Column[
        str | None,
        str | None,
        str | None,
        Literal["nickname"],
        str,
    ]

    def __init__(self, source: str) -> None:
        self.id = Column("id", source, writable=False)
        self.email = Column("email", source)
        self.nickname = Column("nickname", source, nullable=True)


class Users(Table[UserRow, UserInsert, UserUpdate, UsersColumns]):
    def __init__(self) -> None:
        source = "public.users"
        super().__init__(
            name="users",
            schema="public",
            columns=UsersColumns(source),
            columns_factory=UsersColumns,
        )


users = Users()
