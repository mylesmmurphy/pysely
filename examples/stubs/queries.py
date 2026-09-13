from typing import assert_type

from .db import db


async def names() -> None:
    row = await (
        db.select_from("person")
        .left_join("pet", "person.id", "pet.owner_id")
        .where("person.id", ">", 0)
        .where(lambda eb: eb("pet.name", "like", "%cat%"))
        .select("person.id")
        .select_as("pet.name", "pet_name")
        .execute_take_first_or_throw()
    )
    assert_type(row["id"], int)
    assert_type(row["pet_name"], str | None)
