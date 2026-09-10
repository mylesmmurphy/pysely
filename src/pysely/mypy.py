from __future__ import annotations

from collections.abc import Callable

from mypy.nodes import DictExpr, ListExpr, StrExpr, TupleExpr, Var
from mypy.plugin import MethodContext, Plugin
from mypy.subtypes import is_subtype
from mypy.types import Instance, Type, TypedDictType, get_proper_type

BUILDER = "pysely.query_builder.schema_query_builder.SchemaQueryBuilder"
INSERT_BUILDER = "pysely.query_builder.write_query_builder.InsertQueryBuilder"
UPDATE_BUILDER = "pysely.query_builder.write_query_builder.UpdateQueryBuilder"


def fields(value: Type) -> dict[str, Type]:
    proper = get_proper_type(value)
    if isinstance(proper, TypedDictType):
        return proper.items
    if isinstance(proper, Instance):
        return {
            name: symbol.node.type
            for base in reversed(proper.type.mro)
            for name, symbol in base.names.items()
            if isinstance(symbol.node, Var) and symbol.node.type is not None
        }
    return {}


def record(ctx: MethodContext, items: dict[str, Type]) -> TypedDictType:
    return TypedDictType(
        items, set(items), set(), ctx.api.named_generic_type("typing._TypedDict", [])
    )


def literal(ctx: MethodContext, index: int) -> str | None:
    if index >= len(ctx.args) or not ctx.args[index]:
        return None
    expression = ctx.args[index][0]
    return expression.value if isinstance(expression, StrExpr) else None


def add_table(
    ctx: MethodContext, database: Type, scope: dict[str, Type], name: str
) -> dict[str, Type]:
    table, _, alias = name.partition(" as ")
    tables = fields(database)
    if table not in tables:
        ctx.api.fail(f"Unknown table: {table}", ctx.context)
        return scope
    key = alias or table
    if key in scope:
        ctx.api.fail(f"Duplicate table alias: {key}", ctx.context)
    return {**scope, key: tables[table]}


def column_type(ctx: MethodContext, scope: dict[str, Type], name: str) -> Type | None:
    parts = name.rsplit(".", 1)
    matches = [
        columns[parts[-1]]
        for alias, row in scope.items()
        if (len(parts) == 1 or alias == parts[0])
        and parts[-1] in (columns := fields(row))
    ]
    if len(matches) == 1:
        return matches[0]
    reason = "Ambiguous column" if matches else "Unknown column in query scope"
    ctx.api.fail(f"{reason}: {name}", ctx.context)
    return None


def select_from(ctx: MethodContext) -> Type:
    owner = get_proper_type(ctx.type)
    result = get_proper_type(ctx.default_return_type)
    name = literal(ctx, 0)
    if (
        not isinstance(owner, Instance)
        or not isinstance(result, Instance)
        or result.type.fullname != BUILDER
        or name is None
    ):
        return ctx.default_return_type
    database = owner.args[0]
    scope = add_table(ctx, database, {}, name)
    return Instance(result.type, [database, record(ctx, scope), record(ctx, {})])


def write_from(ctx: MethodContext) -> Type:
    owner = get_proper_type(ctx.type)
    result = get_proper_type(ctx.default_return_type)
    name = literal(ctx, 0)
    if (
        not isinstance(owner, Instance)
        or not isinstance(result, Instance)
        or name is None
    ):
        return ctx.default_return_type
    table, _, _ = name.partition(" as ")
    tables = fields(owner.args[0])
    if table not in tables:
        ctx.api.fail(f"Unknown table: {table}", ctx.context)
        return result
    if result.type.fullname in {INSERT_BUILDER, UPDATE_BUILDER}:
        return Instance(result.type, [tables[table], result.args[1]])
    return result


def write_values(ctx: MethodContext) -> Type:
    owner = get_proper_type(ctx.type)
    if not isinstance(owner, Instance) or not ctx.args[0]:
        return ctx.default_return_type
    expression = ctx.args[0][0]
    if not isinstance(expression, DictExpr):
        return owner
    columns = fields(owner.args[0])
    for key, value in expression.items:
        if not isinstance(key, StrExpr):
            continue
        expected = columns.get(key.value)
        if expected is None:
            ctx.api.fail(f"Unknown write column: {key.value}", key)
        elif not is_subtype(ctx.api.get_expression_type(value), expected):
            ctx.api.fail(f"Incompatible value for column {key.value}", value)
    return owner


def write_method(method: str) -> Callable[[MethodContext], Type]:
    def hook(ctx: MethodContext) -> Type:
        owner = get_proper_type(ctx.type)
        if not isinstance(owner, Instance):
            return ctx.default_return_type
        row = owner.args[0]
        columns = fields(row)
        if not columns:
            return ctx.default_return_type
        if method == "where":
            name = literal(ctx, 0)
            if name is None:
                return owner
            expected = columns.get(name.rsplit(".", 1)[-1])
            if expected is None:
                ctx.api.fail(f"Unknown column in query scope: {name}", ctx.context)
            elif ctx.arg_types[2] and not is_subtype(ctx.arg_types[2][0], expected):
                ctx.api.fail(f"Incompatible value for column {name}", ctx.context)
            return owner

        expressions = [item for group in ctx.args for item in group]
        if len(expressions) == 1 and isinstance(expressions[0], ListExpr | TupleExpr):
            expressions = expressions[0].items
        selected: dict[str, Type] = {}
        for item in expressions:
            if not isinstance(item, StrExpr):
                return ctx.default_return_type
            name, _, alias = item.value.partition(" as ")
            value = columns.get(name.rsplit(".", 1)[-1])
            if value is None:
                ctx.api.fail(f"Unknown column in query scope: {name}", item)
            else:
                selected[alias or name.rsplit(".", 1)[-1]] = value
        result = ctx.api.named_generic_type("builtins.list", [record(ctx, selected)])
        return Instance(owner.type, [row, result])

    return hook


def query_method(method: str) -> Callable[[MethodContext], Type]:
    def hook(ctx: MethodContext) -> Type:
        owner = get_proper_type(ctx.type)
        if not isinstance(owner, Instance):
            return ctx.default_return_type
        database, scope_type, row = owner.args
        scope = fields(scope_type)
        if not scope:
            return ctx.default_return_type
        if method == "inner_join":
            table = literal(ctx, 0)
            if table is None:
                return ctx.default_return_type
            scope = add_table(ctx, database, scope, table)
            for index in (1, 2):
                name = literal(ctx, index)
                if name is not None:
                    column_type(ctx, scope, name)
            return Instance(owner.type, [database, record(ctx, scope), row])
        if method == "where":
            name = literal(ctx, 0)
            expected = column_type(ctx, scope, name) if name is not None else None
            if (
                expected is not None
                and ctx.arg_types[2]
                and not is_subtype(ctx.arg_types[2][0], expected)
            ):
                ctx.api.fail(f"Incompatible value for column {name}", ctx.context)
            return owner
        expression = ctx.args[0][0]
        expressions = (
            expression.items
            if isinstance(expression, ListExpr | TupleExpr)
            else [expression]
        )
        selected = dict(fields(row))
        for item in expressions:
            if not isinstance(item, StrExpr):
                unknown_row = ctx.api.named_generic_type(
                    "builtins.dict",
                    [
                        ctx.api.named_generic_type("builtins.str", []),
                        ctx.api.named_generic_type("builtins.object", []),
                    ],
                )
                return Instance(owner.type, [database, scope_type, unknown_row])
            name, _, alias = item.value.partition(" as ")
            value = column_type(ctx, scope, name)
            if value is not None:
                selected[alias or name.rsplit(".", 1)[-1]] = value
        return Instance(owner.type, [database, scope_type, record(ctx, selected)])

    return hook


class PyselyPlugin(Plugin):
    def get_method_hook(self, fullname: str) -> Callable[[MethodContext], Type] | None:
        if fullname == "pysely.pysely.Pysely.select_from":
            return select_from
        if fullname in {
            "pysely.pysely.Pysely.insert_into",
            "pysely.pysely.Pysely.update_table",
            "pysely.pysely.Pysely.delete_from",
        }:
            return write_from
        for method in ("select", "where", "inner_join"):
            if fullname == f"{BUILDER}.{method}":
                return query_method(method)
        if fullname in {f"{INSERT_BUILDER}.values", f"{UPDATE_BUILDER}.set"}:
            return write_values
        for builder in (INSERT_BUILDER, UPDATE_BUILDER):
            for method in ("where", "returning"):
                if fullname == f"{builder}.{method}":
                    return write_method(method)
        return None


def plugin(version: str) -> type[Plugin]:
    return PyselyPlugin
