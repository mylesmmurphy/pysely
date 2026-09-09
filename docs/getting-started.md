# Getting started

## Install from source

Pysely is not published to PyPI yet. Clone the repository and install the driver
extra for your database:

```bash
git clone https://github.com/mylesmmurphy/pysely.git
cd pysely
uv sync --extra sqlite
```

Use `postgres` or `mysql` instead of `sqlite` for those databases.

## Define a table

Pysely keeps row, insert, and update shapes separate. Generated schemas will
produce these definitions; they can also be written directly today.

```python
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
    nickname: Column[str | None, str | None, str | None, Literal["nickname"], str]

    def __init__(self, source: str) -> None:
        self.id = Column("id", source, writable=False)
        self.email = Column("email", source)
        self.nickname = Column("nickname", source, nullable=True)


users = Table[UserRow, UserInsert, UserUpdate, UsersColumns](
    name="users",
    columns=UsersColumns("users"),
    columns_factory=UsersColumns,
)
```

## Connect and query

```python
from pysely import Pysely, SqliteDialect


async with Pysely[object](dialect=SqliteDialect("app.db")) as db:
    rows = await db.select_from(users).select(users.c.id, users.c.email).execute()
```

All values are passed separately from the generated SQL as driver parameters.
