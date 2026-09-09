import pytest

from pysely import (
    MssqlDialect,
    MysqlDialect,
    PGliteDialect,
    PostgresDialect,
    Pysely,
    SqliteDialect,
    and_,
    or_,
)
from test.fixtures.generated import users


@pytest.mark.parametrize(
    ("dialect", "placeholder", "quote"),
    [
        (PostgresDialect(), "$1", '"'),
        (MysqlDialect(), "%s", "`"),
        (SqliteDialect(), "?", '"'),
        (MssqlDialect(), "?", "["),
        (PGliteDialect(), "$1", '"'),
    ],
)
def test_select_with_bound_predicate(dialect, placeholder, quote):
    db = Pysely[object](dialect=dialect)

    compiled = (
        db.select_from(users)
        .select(users.c.id, users.c.email.as_("login"))
        .where(users.c.email.eq("myles@example.com"))
        .compile()
    )

    if quote == "[":
        assert compiled.sql == (
            "select [public].[users].[id], [public].[users].[email] as [login] "
            f"from [public].[users] where [public].[users].[email] = {placeholder}"
        )
    else:
        assert compiled.sql == (
            f"select {quote}public{quote}.{quote}users{quote}.{quote}id{quote}, "
            f"{quote}public{quote}.{quote}users{quote}.{quote}email{quote} "
            f"as {quote}login{quote} from {quote}public{quote}.{quote}users{quote} "
            f"where {quote}public{quote}.{quote}users{quote}.{quote}email{quote} "
            f"= {placeholder}"
        )
    assert compiled.parameters == ("myles@example.com",)


def test_builder_branches_do_not_mutate_each_other():
    db = Pysely[object](dialect=PostgresDialect())
    base = db.select_from(users).select(users.c.id)

    first = base.where(users.c.email.eq("first@example.com"))
    second = base.where(users.c.email.eq("second@example.com"))

    assert base.compile().parameters == ()
    assert first.compile().parameters == ("first@example.com",)
    assert second.compile().parameters == ("second@example.com",)


def test_none_comparison_uses_is_null():
    db = Pysely[object](dialect=PostgresDialect())

    compiled = (
        db.select_from(users)
        .select(users.c.id)
        .where(users.c.nickname.eq(None))
        .compile()
    )

    assert compiled.sql.endswith('"public"."users"."nickname" is null')
    assert compiled.parameters == ()


def test_expression_rejects_python_truth_testing():
    with pytest.raises(TypeError, match="SQL expressions"):
        bool(users.c.id.eq(1))


def test_alias_rebinds_columns_without_mutating_table():
    user_alias = users.as_("u")
    db = Pysely[object](dialect=PostgresDialect())

    compiled = db.select_from(user_alias).select(user_alias.c.id).compile()

    assert compiled.sql == 'select "u"."id" from "public"."users" as "u"'
    assert users.c.id.source == "public.users"


def test_boolean_groups_preserve_parentheses_and_binding_order():
    db = Pysely[object](dialect=PostgresDialect())

    compiled = (
        db.select_from(users)
        .select(users.c.id)
        .where(
            and_(
                users.c.id.eq(1),
                or_(
                    users.c.email.eq("ada@example.com"),
                    users.c.email.eq("grace@example.com"),
                ),
            )
        )
        .compile()
    )

    assert compiled.sql.endswith(
        'where ("public"."users"."id" = $1 and '
        '("public"."users"."email" = $2 or '
        '"public"."users"."email" = $3))'
    )
    assert compiled.parameters == (1, "ada@example.com", "grace@example.com")


def test_where_ref_compares_columns_without_binding_values():
    db = Pysely[object](dialect=PostgresDialect())

    compiled = (
        db.select_from(users)
        .select(users.c.id)
        .where_ref(users.c.email, "!=", users.c.nickname)
        .compile()
    )

    assert compiled.sql.endswith(
        'where "public"."users"."email" != "public"."users"."nickname"'
    )
    assert compiled.parameters == ()
