"""Generate only adjacent type stubs for handwritten Pysely schemas.

Parsing never imports the schema or connects to a database. Shared predicate
buckets avoid per-table predicate overloads; exact projection overloads retain
column-to-key mappings. Variadic field packs replace nested result-row lists.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass

_SINGLE_QUOTED = re.compile(r"'([^'\"\\]*)'")

# Names the generated module defines itself, so the schema cannot use them.
RESERVED_NAMES = frozenset(
    {
        "DatabaseClient",
        "DatabaseExpressionBuilder",
        "DatabaseQuery",
        "SingleTableQuery",
        "TableName",
        "schema",
    }
)

# How many selected fields back an order_by() alias may sit.
ORDER_DEPTH = 8

COMPARE = 'Literal["=", "!=", "<>", "<", "<=", ">", ">="]'
NULL_TEST = 'Literal["is", "is not"]'
PATTERN = 'Literal["like", "not like"]'
COLLECTION = 'Literal["in", "not in"]'


class SchemaError(ValueError):
    """Raised when a schema module cannot be turned into a typed interface."""


# --- schema model -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Column:
    name: str
    annotation: str
    """The annotation as written, with double quotes."""
    value: str
    """The annotation without ``None``: what comparisons bind."""
    nullable: bool


@dataclass(frozen=True, slots=True)
class Table:
    attribute: str
    class_name: str
    alias: str
    """Prefix of the generated names: ``PersonColumns``, ``PersonQuery``..."""
    columns: tuple[Column, ...]

    @property
    def columns_alias(self) -> str:
        return f"{self.alias}Columns"

    @property
    def scope_alias(self) -> str:
        return f"{self.alias}Scope"

    @property
    def query_class(self) -> str:
        return f"{self.alias}Query"

    @property
    def token(self) -> str:
        return f'Literal["{self.attribute}"]'


@dataclass(frozen=True, slots=True)
class SchemaModel:
    database: str
    tables: tuple[Table, ...]
    imports: tuple[str, ...]
    body: tuple[str, ...]
    """Every top-level statement that is not an import, re-rendered as source."""

    def shared(self, column: str) -> bool:
        """Whether another table also declares this column name."""
        return (
            sum(
                any(item.name == column for item in other.columns)
                for other in self.tables
            )
            > 1
        )

    def spellings(self, table: Table, column: str) -> list[str]:
        """Every way to write a column while its table is the only one in scope."""
        return [f"{table.attribute}.{column}", column]

    def references(self, table: Table, column: str) -> list[str]:
        """Spellings that stay unambiguous after a join: qualified, bare when unique."""
        names = [f"{table.attribute}.{column}"]
        if not self.shared(column):
            names.append(column)
        return names

    def column_literals(self, table: Table) -> list[str]:
        """All spellings for a single-table query, qualified names first."""
        return [f"{table.attribute}.{column.name}" for column in table.columns] + [
            column.name for column in table.columns
        ]

    def scope_literals(self, table: Table) -> list[str]:
        """The spellings a table contributes to a multi-table scope."""
        references = [self.references(table, column.name) for column in table.columns]
        return [names[0] for names in references] + [
            names[1] for names in references if len(names) > 1
        ]


# --- annotation analysis ----------------------------------------------------


def _annotation(node: ast.expr) -> str:
    """Unparse an annotation using the double quotes ruff format expects."""
    return _SINGLE_QUOTED.sub(r'"\1"', ast.unparse(node))


def _is_none(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _strip_none(node: ast.expr) -> tuple[ast.expr, bool]:
    """Split ``X | None``, ``Optional[X]`` and ``Union[X, None]`` into X."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left, left_null = _strip_none(node.left)
        right, right_null = _strip_none(node.right)
        if _is_none(node.left):
            return right, True
        if _is_none(node.right):
            return left, True
        if left_null or right_null:
            return ast.BinOp(left, ast.BitOr(), right), True
        return node, False
    if isinstance(node, ast.Subscript):
        head = node.value
        name = head.id if isinstance(head, ast.Name) else getattr(head, "attr", "")
        if name == "Optional":
            inner, _ = _strip_none(node.slice)
            return inner, True
        if name == "Union":
            items = list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else []
            kept = [item for item in items if not _is_none(item)]
            if items and len(kept) < len(items):
                if len(kept) == 1:
                    return kept[0], True
                return ast.Subscript(
                    head, ast.Tuple(kept, ast.Load()), ast.Load()
                ), True
    return node, False


def _nullable(value: str) -> str:
    return f"{value} | None"


def _string_like(value: str) -> bool:
    if value in {"str", "LiteralString"}:
        return True
    if value.startswith("Literal["):
        return all(
            item.strip().startswith('"')
            for item in value[len("Literal[") : -1].split(",")
        )
    return False


# --- parsing ----------------------------------------------------------------


def parse_schema(source: str, *, filename: str = "tables.py") -> SchemaModel:
    """Read annotated classes out of a schema module."""
    tree = ast.parse(source, filename=filename)
    imports = tuple(
        ast.unparse(node)
        for node in tree.body
        if isinstance(node, ast.Import | ast.ImportFrom)
        and not (isinstance(node, ast.ImportFrom) and node.module == "__future__")
    )
    classes: dict[str, dict[str, ast.expr]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        fields: dict[str, ast.expr] = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields[item.target.id] = item.annotation
        classes[node.name] = fields

    def names_class(annotation: ast.expr) -> bool:
        return isinstance(annotation, ast.Name) and annotation.id in classes

    database = next(
        (
            name
            for name, fields in classes.items()
            if fields and all(names_class(value) for value in fields.values())
        ),
        None,
    )
    if database is None:
        raise SchemaError(
            "No database class found: expected a class whose annotations are all "
            "other classes in the same module"
        )
    taken = RESERVED_NAMES & set(classes)
    if taken:
        names = ", ".join(sorted(taken))
        raise SchemaError(
            f"Schema class name reserved by the generated module: {names}. "
            "Rename it (for example DatabaseSchema)."
        )
    tables: list[Table] = []
    for attribute, class_ref in classes[database].items():
        class_name = class_ref.id if isinstance(class_ref, ast.Name) else ""
        columns = classes[class_name]
        if not columns:
            raise SchemaError(f"Table class {class_name} has no annotated columns")
        parsed: list[Column] = []
        for name, annotation in columns.items():
            value, nullable = _strip_none(annotation)
            parsed.append(
                Column(name, _annotation(annotation), _annotation(value), nullable)
            )
        tables.append(
            Table(
                attribute=attribute,
                class_name=class_name,
                alias=class_name.removesuffix("Table"),
                columns=tuple(parsed),
            )
        )
    if not tables:
        raise SchemaError(f"Database class {database} declares no tables")
    body = tuple(
        _SINGLE_QUOTED.sub(r'"\1"', ast.unparse(node))
        for node in tree.body
        if not isinstance(node, ast.Import | ast.ImportFrom)
        and not (isinstance(node, ast.ClassDef) and node.name == database)
    )
    return SchemaModel(
        database=database, tables=tuple(tables), imports=imports, body=body
    )


# --- direct stub rendering --------------------------------------------------


def _literal(names: list[str]) -> str:
    return f"Literal[{', '.join(repr(name) for name in names)}]" if names else "Never"


class _Renderer:
    """Emit final stub signatures, without runtime twins or a legacy type IR."""

    def __init__(self, model: SchemaModel, values: list[str]) -> None:
        self.model = model
        self.values = values
        self.group_vars = [f"G{i}" for i in range(len(values))]
        self.lines: list[str] = []
        owners: dict[str, int] = {}
        for table in model.tables:
            for column in table.columns:
                owners[column.name] = owners.get(column.name, 0) + 1
        self.shared = {name for name, count in owners.items() if count > 1}
        self.group_cache: dict[tuple[str, bool], list[str]] = {}

    def references(
        self, table: Table, column: Column, *, bare: bool = False
    ) -> list[str]:
        names = [f"{table.attribute}.{column.name}"]
        if bare or column.name not in self.shared:
            names.append(column.name)
        return names

    def groups(self, table: Table, *, bare: bool = False) -> list[str]:
        key = (table.attribute, bare)
        if key not in self.group_cache:
            self.group_cache[key] = [
                _literal(
                    [
                        name
                        for column in table.columns
                        if column.value == value
                        for name in self.references(table, column, bare=bare)
                    ]
                )
                for value in self.values
            ]
        return self.group_cache[key]

    def by_value(
        self, table: Table, *, bare: bool = False
    ) -> dict[tuple[str, bool], list[str]]:
        groups: dict[tuple[str, bool], list[str]] = {}
        for column in table.columns:
            groups.setdefault((column.value, column.nullable), []).extend(
                self.references(table, column, bare=bare)
            )
        return groups

    def overload(self, name: str, parameters: str, returns: str) -> None:
        self.lines.extend(
            [
                "    @overload",
                f"    def {name}({parameters}) -> {returns}: ...",
            ]
        )

    def joined(
        self,
        tables: str = "TablesT",
        columns: str = "ColumnT",
        null: str = "NullT",
        star: str = "StarT",
        fields: str = "*FieldsT",
        groups: list[str] | None = None,
    ) -> str:
        args = [
            tables,
            columns,
            null,
            star,
            *(self.group_vars if groups is None else groups),
            fields,
        ]
        return f"DatabaseQuery[{', '.join(args)}]"

    def ordering(self, query: Callable[[str], str], columns: str) -> None:
        self.overload(
            "order_by",
            f"self, column: {columns}, direction: OrderDirection = 'asc'",
            query("*FieldsT"),
        )
        for depth in range(1, ORDER_DEPTH + 1):
            fields = ", ".join(
                [
                    *(f"Field[K{i}, V{i}]" for i in range(1, depth + 1)),
                    "*RestT",
                ]
            )
            receiver = query(fields)
            self.overload(
                "order_by",
                f"self: {receiver}, column: K{depth}, "
                "direction: OrderDirection = 'asc'",
                receiver,
            )

    def join_methods(self, *, single: bool = False) -> None:
        tables, columns, null, star = (
            ("TableT", "ScopeT", "Never", "Literal['']")
            if single
            else ("TablesT", "ColumnT", "NullT", "StarT")
        )
        for kind in ("inner", "left", "right", "full"):
            for table in self.model.tables:
                scope = f"{columns} | {table.scope_alias}"
                nullable = (
                    f"{null} | {table.token}" if kind in {"left", "full"} else null
                )
                marked = "Literal['*']" if kind in {"right", "full"} else star
                groups = [
                    f"{old} | {new}"
                    for old, new in zip(
                        self.group_vars, self.groups(table), strict=True
                    )
                ]
                self.overload(
                    f"{kind}_join",
                    f"self, table: {table.token}, left: {scope}, right: {scope}",
                    self.joined(
                        f"{tables} | {table.token}",
                        scope,
                        nullable,
                        marked,
                        groups=groups,
                    ),
                )

    def joined_query(self) -> None:
        groups = ", ".join(self.group_vars)
        builder = f"DatabaseExpressionBuilder[ColumnT, {groups}]"
        self.lines.append(
            f"class DatabaseQuery(_Predicates[{builder}, ColumnT, {groups}], "
            "_QueryScope[TablesT, NullT], QueryCore[ColumnT, StarT, *FieldsT], "
            f"Generic[TablesT, ColumnT, NullT, StarT, {groups}, *FieldsT]):"
        )
        for table in self.model.tables:
            tables = f"TablesT | {table.token}"
            for column in table.columns:
                # Already-nullable values need no outer-join-specific overload.
                variants = [("NullT", column.annotation)]
                if not column.nullable:
                    variants.insert(
                        0, (f"NullT | {table.token}", _nullable(column.value))
                    )
                for null, value in variants:
                    # Scope-only receivers avoid mypy widening variadic field packs.
                    self.overload(
                        "select",
                        f"self: _QueryScope[{tables}, {null}], "
                        f"selections: {_literal(self.references(table, column))}",
                        self.joined(
                            tables=tables,
                            null=null,
                            fields=f"Field[Literal[{column.name!r}], {value}], "
                            "*FieldsT",
                        ),
                    )
        self.overload(
            "select",
            "self, selections: ColumnT | Sequence[ColumnT]",
            self.joined(fields="Field[str, object], *FieldsT"),
        )
        for table in self.model.tables:
            tables = f"TablesT | {table.token}"
            for (value, nullable), names in self.by_value(table).items():
                variants = [("NullT", _nullable(value) if nullable else value)]
                if not nullable:
                    variants.insert(0, (f"NullT | {table.token}", _nullable(value)))
                for null, read in variants:
                    self.overload(
                        "select_as",
                        f"self: _QueryScope[{tables}, {null}], "
                        f"source: {_literal(names)}, alias: AliasT",
                        self.joined(
                            tables=tables,
                            null=null,
                            fields=f"Field[AliasT, {read}], *FieldsT",
                        ),
                    )
        self.overload(
            "select_as",
            "self, source: ColumnT, alias: str",
            self.joined(fields="Field[str, object], *FieldsT"),
        )
        self.ordering(lambda fields: self.joined(fields=fields), "ColumnT")
        self.join_methods()

    def single_table_base(self) -> None:
        groups = ", ".join(self.group_vars)
        self.lines.append(
            "class SingleTableQuery(QueryCore[ColumnsT, Literal[''], *FieldsT], "
            f"Generic[TableT, ColumnsT, ScopeT, {groups}, *FieldsT]):"
        )
        self.join_methods(single=True)

    def table_query(self, table: Table) -> None:
        groups = ", ".join(self.groups(table, bare=True))
        scoped = ", ".join(self.groups(table))
        columns = table.columns_alias
        builder = f"DatabaseExpressionBuilder[{columns}, {groups}]"
        self.lines.append(
            f"class {table.query_class}(_Predicates[{builder}, {columns}, {groups}], "
            f"SingleTableQuery[{table.token}, {columns}, {table.scope_alias}, "
            f"{scoped}, *FieldsT], "
            "Generic[*FieldsT,]):"
        )

        def query(fields: str) -> str:
            # Preserve canonical trailing commas in single-pack subscriptions.
            return f"{table.query_class}[{fields}{',' if fields == '*FieldsT' else ''}]"

        for column in table.columns:
            selections = _literal(self.references(table, column, bare=True))
            self.overload(
                "select",
                f"self, selections: {selections}",
                query(
                    f"Field[Literal[{column.name!r}], {column.annotation}], *FieldsT"
                ),
            )
        self.overload(
            "select",
            f"self, selections: {columns} | Sequence[{columns}]",
            query("Field[str, object], *FieldsT"),
        )
        for (value, nullable), names in self.by_value(table, bare=True).items():
            read = _nullable(value) if nullable else value
            self.overload(
                "select_as",
                f"self, source: {_literal(names)}, alias: AliasT",
                query(f"Field[AliasT, {read}], *FieldsT"),
            )
        self.overload(
            "select_as",
            f"self, source: {columns}, alias: str",
            query("Field[str, object], *FieldsT"),
        )
        self.ordering(query, columns)

    def render(self) -> str:
        self.lines.extend(
            [
                "from __future__ import annotations",
                *self.model.imports,
                "from collections.abc import Callable, Sequence",
                "from typing import Generic, Literal, LiteralString, Never, "
                "TypeAlias, TypeVar, overload",
                *self.model.body,
            ]
        )
        for table in self.model.tables:
            self.lines.extend(
                [
                    f"{table.columns_alias}: TypeAlias = "
                    f"{_literal(self.model.column_literals(table))}",
                    f"{table.scope_alias}: TypeAlias = "
                    f"{_literal(self.model.scope_literals(table))}",
                ]
            )
        self.lines.append(
            "TableName: TypeAlias = "
            f"{_literal([t.attribute for t in self.model.tables])}"
        )
        for name in ("TableT", "TablesT", "ColumnsT", "ColumnT", "ScopeT", "NullT"):
            self.lines.append(f"{name} = TypeVar({name!r}, bound=str)")
        self.lines.extend(
            [
                "FieldsT = TypeVarTuple('FieldsT')",
                "StarT = TypeVar('StarT', bound=str)",
                "AliasT = TypeVar('AliasT', bound=LiteralString | Literal[''])",
                "RestT = TypeVarTuple('RestT')",
                *(
                    f"K{i} = TypeVar('K{i}', bound=str)"
                    for i in range(1, ORDER_DEPTH + 1)
                ),
                *(f"V{i} = TypeVar('V{i}')" for i in range(1, ORDER_DEPTH + 1)),
            ]
        )
        self.joined_query()
        self.single_table_base()
        for table in self.model.tables:
            self.table_query(table)
        return "\n".join(self.lines)


# Keep generated modules below Pyright's observed code-flow complexity ceiling.
PYRIGHT_DEFINITION_CEILING = 14_000


class _StubCleanup(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        node.body = [ast.Expr(value=ast.Constant(value=Ellipsis))]
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.expr:
        self.generic_visit(node)
        if isinstance(node.op, ast.BitOr):
            if isinstance(node.left, ast.Name) and node.left.id == "Never":
                return node.right
            if isinstance(node.right, ast.Name) and node.right.id == "Never":
                return node.left
        return node


def _predicates(values: list[str]) -> str:
    groups = [f"G{i}" for i in range(len(values))]
    lines = [
        *(f'{g} = TypeVar("{g}", bound=str)' for g in groups),
        'BuilderT = TypeVar("BuilderT")',
    ]
    for builder in (True, False):
        if builder:
            lines.append(
                "class DatabaseExpressionBuilder(ExpressionBuilder[ColumnT], "
                f"Generic[ColumnT, {', '.join(groups)}]):"
            )
        else:
            lines.append(
                f"class _Predicates(Generic[BuilderT, ColumnT, {', '.join(groups)}]):"
            )
        method, returns = (
            ("__call__", "Expression[bool]") if builder else ("where", "Self")
        )
        for group, value in zip(groups, values, strict=True):
            shapes = [
                (COMPARE, value),
                (COLLECTION, f"list[{value}] | tuple[{value}, ...]"),
            ]
            if _string_like(value):
                shapes.append((PATTERN, "str"))
            for operator, shape in shapes:
                lines += [
                    "    @overload",
                    f"    def {method}(self, column: {group}, "
                    f"operator: {operator}, value: {shape}) -> {returns}: ...",
                ]
        lines += [
            "    @overload",
            f"    def {method}(self, column: ColumnT, "
            f"operator: {NULL_TEST}, value: None) -> {returns}: ...",
        ]
        if not builder:
            lines += [
                "    @overload",
                "    def where(self, column: Callable[[BuilderT], "
                "Expression[bool]]) -> Self: ...",
                "    def having(self, column: Callable[[BuilderT], "
                "Expression[bool]]) -> Self: ...",
            ]
    return "\n".join(lines)


def generate_stub(source: str, *, source_name: str = "dbschema.py") -> str:
    """Generate an adjacent stub without importing/executing the input module."""
    model = parse_schema(source, filename=source_name)
    original = ast.parse(source)
    schema = next(
        n
        for n in original.body
        if isinstance(n, ast.ClassDef) and n.name == model.database
    )
    if not any(
        ast.unparse(base).split(".")[-1] == "SchemaDefinition" for base in schema.bases
    ):
        raise SchemaError(
            f"{model.database} must inherit SchemaDefinition for stub generation"
        )
    # Stub declarations are an interface, not a copy of arbitrary executable code.
    if any(
        not isinstance(
            n, ast.Import | ast.ImportFrom | ast.ClassDef | ast.Assign | ast.AnnAssign
        )
        and not (
            isinstance(n, ast.Expr)
            and isinstance(n.value, ast.Constant)
            and isinstance(n.value.value, str)
        )
        for n in original.body
    ):
        raise SchemaError(
            "Stub schemas must contain declarative tables, "
            "imports and type aliases only"
        )
    values = list(dict.fromkeys(c.value for t in model.tables for c in t.columns))
    generated_names = {
        "Field",
        "QueryCore",
        "SchemaClient",
        "_QueryScope",
        "_Predicates",
        "TableT",
        "TablesT",
        "ColumnsT",
        "ColumnT",
        "ScopeT",
        "NullT",
        "FieldsT",
        "StarT",
        "AliasT",
        "RestT",
        "BuilderT",
        *(f"G{i}" for i in range(len(values))),
        *(f"K{i}" for i in range(1, ORDER_DEPTH + 1)),
        *(f"V{i}" for i in range(1, ORDER_DEPTH + 1)),
        *(t.query_class for t in model.tables),
        *(t.columns_alias for t in model.tables),
        *(t.scope_alias for t in model.tables),
    }
    declared_names = {n.name for n in original.body if isinstance(n, ast.ClassDef)}
    collisions = generated_names & declared_names
    if collisions:
        raise SchemaError(
            f"Names reserved by the stub: {', '.join(sorted(collisions))}"
        )
    if len({t.alias for t in model.tables}) != len(model.tables):
        raise SchemaError("Each table must have a distinct class/query name")
    tree = ast.parse(_Renderer(model, values).render())
    nodes: list[ast.stmt] = []
    for node in tree.body:
        if (
            (isinstance(node, ast.ClassDef) and node.name == model.database)
            or (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "schema" for t in node.targets
                )
            )
            or (isinstance(node, ast.ImportFrom) and node.module == "pysely")
        ):
            continue
        if not isinstance(node, ast.Expr):
            nodes.append(node)
    extra = ast.parse(
        "from typing import Self, TypeVarTuple\n"
        "from pysely import Dialect, Expression, ExpressionBuilder, "
        "OrderDirection, QueryPlugin, SchemaDefinition\n"
        "from pysely.flat_row import Field\n"
        "from pysely.schema_definition import QueryCore, SchemaClient\n"
        "class _QueryScope(Generic[TablesT, NullT]): ...\n" + _predicates(values)
    ).body
    # Insert shared types before query subclasses, after aliases/TypeVars.
    index = next(
        i
        for i, n in enumerate(nodes)
        if isinstance(n, ast.ClassDef) and n.name == "DatabaseQuery"
    )
    nodes[index:index] = extra
    tail = ["class DatabaseClient(SchemaClient):"]
    for table in model.tables:
        if len(model.tables) > 1:
            tail.append("    @overload")
        tail.append(
            f"    def select_from(self, table: {table.token}) "
            f"-> {table.query_class}[()]: ..."
        )
    tail += [
        f"class {model.database}(SchemaDefinition):",
        *(f"    {t.attribute}: {t.class_name}" for t in model.tables),
        "    @classmethod",
        "    def connect(cls, *, dialect: Dialect, "
        "plugins: tuple[QueryPlugin, ...] = ()) -> DatabaseClient: ...",
    ]
    nodes.extend(ast.parse("\n".join(tail)).body)
    # A .pyi replaces the module interface. Hoist and merge imports before all
    # aliases so formatters/checkers cannot mistake a later import for unused.
    imports: list[ast.stmt] = []
    from_imports: dict[tuple[str | None, int], ast.ImportFrom] = {}
    declarations: list[ast.stmt] = []
    for node in nodes:
        if isinstance(node, ast.ImportFrom):
            key = (node.module, node.level)
            if key not in from_imports:
                from_imports[key] = node
                imports.append(node)
            else:
                existing = from_imports[key]
                known = {(n.name, n.asname) for n in existing.names}
                existing.names.extend(
                    n for n in node.names if (n.name, n.asname) not in known
                )
        elif isinstance(node, ast.Import):
            imports.append(node)
        else:
            declarations.append(node)
    used = {
        n.id
        for statement in declarations
        for n in ast.walk(statement)
        if isinstance(n, ast.Name)
    }
    for node in imports:
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            node.names = [n for n in node.names if n.name != "Any" or "Any" in used]
    module = ast.fix_missing_locations(
        ast.Module(body=imports + declarations, type_ignores=[])
    )
    _StubCleanup().visit(module)
    # A one-table schema has one join signature, not an overload set.
    for cls in (n for n in module.body if isinstance(n, ast.ClassDef)):
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
        counts: dict[str, int] = {}
        for method in methods:
            counts[method.name] = counts.get(method.name, 0) + 1
        for method in methods:
            if counts[method.name] == 1:
                method.decorator_list = [
                    d for d in method.decorator_list if ast.unparse(d) != "overload"
                ]
    definitions = sum(isinstance(n, ast.FunctionDef) for n in ast.walk(module))
    if definitions > PYRIGHT_DEFINITION_CEILING:
        raise SchemaError(
            f"Stub needs {definitions} definitions, exceeding the checker budget"
        )
    header = f'"""Generated from {source_name}; type-only. Do not edit."""\n\n'
    header += "# ruff: noqa: E501, I001\n# fmt: off\n"
    # Mypy treats LiteralString as str; the dynamic-alias fallback can therefore
    # look unreachable for a table with only one value family.
    header += '# mypy: disable-error-code="override, overload-overlap, '
    header += 'overload-cannot-match"\n'
    header += "# pyright: reportIncompatibleMethodOverride=false\n"
    header += "# pyright: reportOverlappingOverload=false\n"
    return header + re.sub(r":\n[ \t]+\.\.\.", ": ...", ast.unparse(module)) + "\n"


def generate(
    source: str, *, source_name: str = "dbschema.py", output: str = "dbschema.pyi"
) -> str:
    """Generate the typing interface for an existing handwritten schema module."""
    if not output.endswith(".pyi"):
        raise SchemaError(
            "Typgen only writes .pyi stubs; keep the schema .py handwritten"
        )
    return generate_stub(source, source_name=source_name)
