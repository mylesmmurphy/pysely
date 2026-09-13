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
from typing import TypeAlias

_SINGLE_QUOTED = re.compile(r"'([^'\"\\]*)'")

LINE_LENGTH = 88

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


# --- rendering helpers ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Sub:
    """A subscripted type expression, rendered the way ruff format would."""

    name: str
    args: tuple[TypeExpr, ...]


TypeExpr: TypeAlias = "str | Sub | Union"


def _one_line(expr: TypeExpr) -> str:
    if isinstance(expr, str):
        return expr
    if isinstance(expr, Union):
        return " | ".join(_one_line(item) for item in expr.items)
    return f"{expr.name}[{', '.join(_one_line(arg) for arg in expr.args)}]"


def _render_type(expr: TypeExpr, indent: int, *, first: int, last: int) -> list[str]:
    """Render a type; ``first``/``last`` are the widths already used around it."""
    single = _one_line(expr)
    if isinstance(expr, str) or first + len(single) + last <= LINE_LENGTH:
        return [single]
    if isinstance(expr, Union):
        # ruff splits a long union one member per line, leading with `|`.
        pad = " " * indent
        lines = _render_type(expr.items[0], indent, first=first, last=0)
        for position, item in enumerate(expr.items[1:], start=2):
            width = last if position == len(expr.items) else 0
            rendered = _render_type(item, indent, first=indent + 2, last=width)
            lines.append(f"{pad}| {rendered[0]}")
            lines.extend(rendered[1:])
        return lines
    pad = " " * indent
    inner = " " * (indent + 4)
    joined = ", ".join(_one_line(arg) for arg in expr.args)
    if len(inner) + len(joined) <= LINE_LENGTH:
        return [f"{expr.name}[", f"{inner}{joined}", f"{pad}]"]
    lines = [f"{expr.name}["]
    for arg in expr.args:
        rendered = _render_type(arg, indent + 4, first=len(inner), last=1)
        rendered[-1] += ","
        lines.append(f"{inner}{rendered[0]}")
        lines.extend(rendered[1:])
    lines.append(f"{pad}]")
    return lines


def _literal(names: list[str]) -> Sub:
    return Sub("Literal", tuple(f'"{name}"' for name in names))


@dataclass(frozen=True, slots=True)
class Union:
    """``a | b | Sub[...]``: only a trailing subscript is ever broken."""

    items: tuple[TypeExpr, ...]


def _signature(
    name: str,
    parameters: list[tuple[str, TypeExpr | None]],
    returns: TypeExpr,
    indent: int = 4,
    body: str = " ...",
) -> list[str]:
    """Render ``def name(params) -> returns:`` the way ruff format would."""
    pad = " " * indent
    params = [
        f"{param}: {_one_line(annotation)}" if annotation is not None else param
        for param, annotation in parameters
    ]
    single = f"{pad}def {name}({', '.join(params)}) -> {_one_line(returns)}:{body}"
    if len(single) <= LINE_LENGTH:
        return [single]
    lines = [f"{pad}def {name}("]
    inner = " " * (indent + 4)
    joined = ", ".join(params)
    if len(inner) + len(joined) <= LINE_LENGTH:
        lines.append(f"{inner}{joined}")
    else:
        for param, annotation in parameters:
            if annotation is None:
                lines.append(f"{inner}{param},")
                continue
            rendered = _render_type(
                annotation, indent + 4, first=len(inner) + len(param) + 2, last=1
            )
            rendered[-1] += ","
            lines.append(f"{inner}{param}: {rendered[0]}")
            lines.extend(rendered[1:])
    tail = _render_type(returns, indent, first=len(pad) + 5, last=1 + len(body))
    lines.append(f"{pad}) -> {tail[0]}" + (f":{body}" if len(tail) == 1 else ""))
    if len(tail) > 1:
        lines.extend(tail[1:-1])
        lines.append(f"{tail[-1]}:{body}")
    return lines


def _import_order(name: str) -> tuple[int, str]:
    """isort's default order-by-type: CONSTANTS, then Classes, then functions."""
    if name.isupper():
        return (0, name)
    if name[:1].isupper():
        return (1, name)
    return (2, name)


# --- rendering --------------------------------------------------------------


class _Renderer:
    def __init__(self, model: SchemaModel) -> None:
        self.model = model
        self.lines: list[str] = []

    # --- helpers

    def emit(self, lines: list[str]) -> None:
        self.lines.extend(lines)

    def overload(
        self,
        name: str,
        parameters: list[tuple[str, TypeExpr | None]],
        returns: TypeExpr,
        indent: int = 8,
    ) -> None:
        pad = " " * indent
        self.emit([f"{pad}@overload"])
        self.emit(_signature(name, parameters, returns, indent))
        self.emit([""])

    @staticmethod
    def joined(
        tables: str, columns: str, null: str, fields: TypeExpr, star: str
    ) -> Sub:
        return Sub("DatabaseQuery", (tables, columns, null, fields, star))

    @staticmethod
    def cons(key: str, value: str, rest: str = "FieldsT") -> Sub:
        return Sub("Cons", (key, value, rest))

    @staticmethod
    def fields_pattern(depth: int) -> Sub:
        """``Cons[K1, V1, Cons[K2, V2, ... RestT]]`` naming every position."""
        inner: TypeExpr = "RestT"
        for position in range(depth, 0, -1):
            inner = Sub("Cons", (f"K{position}", f"V{position}", inner))
        assert isinstance(inner, Sub)
        return inner

    def ordering(self, query: Callable[[TypeExpr], Sub], columns: str) -> None:
        """order_by: a column in scope, or the alias of a selected field."""
        self.overload(
            "order_by",
            [
                ("self", None),
                ("column", columns),
                ('direction: OrderDirection = "asc"', None),
            ],
            query("FieldsT"),
        )
        for depth in range(1, ORDER_DEPTH + 1):
            pattern = self.fields_pattern(depth)
            self.overload(
                "order_by",
                [
                    ("self", query(pattern)),
                    ("column", f"K{depth}"),
                    ('direction: OrderDirection = "asc"', None),
                ],
                query(pattern),
            )
        self.emit(
            [
                "        def order_by(self, column: Any, direction: Any = "
                '"asc") -> Any:',
                "            return self._order_by(column, direction)",
                "",
            ]
        )

    def having(self, query: Sub, builder: str) -> None:
        """having: callback form only, to stay under pyright's per-module
        definition ceiling; the builder carries the typed operator shapes."""
        self.emit(
            _signature(
                "having",
                [
                    ("self", None),
                    (
                        "column",
                        Sub("Callable", (Sub("", (builder,)), "Expression[bool]")),
                    ),
                ],
                query,
                8,
                body="",
            )
        )
        self.emit(["            return self._having(cast(Any, column))", ""])

    def shapes(
        self, table: Table, names_for: Callable[[Column], list[str]]
    ) -> list[tuple[list[str], str, TypeExpr]]:
        """(column names, operator literal, value type) for each where overload."""
        by_value: dict[str, list[str]] = {}
        all_names: list[str] = []
        for column in table.columns:
            names = names_for(column)
            by_value.setdefault(column.value, []).extend(names)
            all_names.extend(names)
        shapes: list[tuple[list[str], str, TypeExpr]] = []
        for value, names in by_value.items():
            shapes.append((names, COMPARE, value))
            shapes.append(
                (
                    names,
                    COLLECTION,
                    Union((Sub("list", (value,)), Sub("tuple", (value, "...")))),
                )
            )
            if _string_like(value):
                shapes.append((names, PATTERN, "str"))
        shapes.append((all_names, NULL_TEST, "None"))
        return shapes

    def scope_names(self, table: Table) -> Callable[[Column], list[str]]:
        return lambda column: self.model.references(table, column.name)

    def all_names(self, table: Table) -> Callable[[Column], list[str]]:
        return lambda column: self.model.spellings(table, column.name)

    def by_value(
        self, table: Table, names_for: Callable[[Column], list[str]]
    ) -> dict[tuple[str, bool], list[str]]:
        groups: dict[tuple[str, bool], list[str]] = {}
        for column in table.columns:
            groups.setdefault((column.value, column.nullable), []).extend(
                names_for(column)
            )
        return groups

    # --- sections

    def render(self, *, source: str, output: str) -> str:
        """Build projection type IR; the stub backend lowers fields and scope."""
        self.emit(["from __future__ import annotations"])
        self.imports()
        for statement in self.model.body:
            self.emit([statement, "", ""])
        self.aliases()
        self.emit(["", "if TYPE_CHECKING:"])
        self.joined_query()
        self.single_table_base()
        for table in self.model.tables:
            self.table_query(table)
        return "\n".join(self.lines)

    def imports(self) -> None:
        typing_names = {
            "TYPE_CHECKING",
            "Any",
            "Generic",
            "Literal",
            "LiteralString",
            "Never",
            "TypeAlias",
            "TypeVar",
            "cast",
            "overload",
        }
        standard: list[tuple[str, list[str]]] = [
            ("collections.abc", ["from collections.abc import Callable, Sequence"]),
        ]
        for item in self.model.imports:
            module = item.split()[1]
            if item.startswith("from typing import "):
                imported = item.removeprefix("from typing import ")
                typing_names.update(name.strip() for name in imported.split(","))
            else:
                standard.append((module, [item]))
        standard.append(
            (
                "typing",
                [
                    "from typing import (",
                    *[
                        f"    {name},"
                        for name in sorted(typing_names, key=_import_order)
                    ],
                    ")",
                ],
            )
        )
        for _, block in sorted(standard, key=lambda entry: entry[0]):
            self.emit(block)

    def aliases(self) -> None:
        model = self.model
        self.emit(
            [
                "# XColumns: every spelling, valid while X is the only table in the",
                "# query. XScope: the spellings that stay unambiguous after a join.",
            ]
        )
        for table in model.tables:
            for name, names in (
                (table.columns_alias, model.column_literals(table)),
                (table.scope_alias, model.scope_literals(table)),
            ):
                self.emit([f"{name}: TypeAlias = Literal["])
                self.emit([f'    "{item}",' for item in names])
                self.emit(["]"])
        table_names = [table.attribute for table in model.tables]
        self.emit(
            [
                f"TableName: TypeAlias = {_one_line(_literal(table_names))}",
                "",
                "# Query state: tables joined, columns in scope, tables joined",
                "# nullably, selected fields (newest first), and whether a right or",
                "# full join made every field nullable.",
                'TableT = TypeVar("TableT", bound=str)',
                'TablesT = TypeVar("TablesT", bound=str)',
                'ColumnsT = TypeVar("ColumnsT", bound=str)',
                'ColumnT = TypeVar("ColumnT", bound=str)',
                'ScopeT = TypeVar("ScopeT", bound=str)',
                'NullT = TypeVar("NullT", bound=str)',
                'FieldsT = TypeVar("FieldsT")',
                'StarT = TypeVar("StarT", bound=str)',
                'AliasT = TypeVar("AliasT", bound=LiteralString | Literal[""])',
                "# Positions in the selected-field list, for ordering by an alias.",
                'RestT = TypeVar("RestT")',
            ]
        )
        self.emit(
            [
                f'K{depth} = TypeVar("K{depth}", bound=str)'
                for depth in range(1, ORDER_DEPTH + 1)
            ]
            + [f'V{depth} = TypeVar("V{depth}")' for depth in range(1, ORDER_DEPTH + 1)]
        )

    # --- expression builders

    def builder_impl(self) -> None:
        self.emit(
            _signature(
                "__call__",
                [
                    ("self", None),
                    ("column", "Any"),
                    ("operator", "Any"),
                    ("value", "Any"),
                ],
                "Expression[bool]",
                8,
                body="",
            )
        )
        self.emit(["            return super().__call__(column, operator, value)", ""])

    def select_impls(self) -> None:
        self.emit(
            [
                "        def select(self, selections: Any) -> Any:",
                "            return super().select(selections)",
                "",
            ]
        )

    def joined_query(self) -> None:
        model = self.model
        self.emit(
            [
                "    # Joined queries. One overload per column; the nullable form",
                "    # comes first and only matches once its table is outer-joined.",
                "    class DatabaseQuery(",
                f'        TypedSchemaQueryBuilder["{model.database}", ColumnT, '
                "FieldsT, StarT],",
                "        Generic[TablesT, ColumnT, NullT, FieldsT, StarT],",
                "    ):",
            ]
        )
        for table in model.tables:
            tables = f"TablesT | {table.token}"
            nullable = f"NullT | {table.token}"
            for column in table.columns:
                selections = _literal(model.references(table, column.name))
                key = f'Literal["{column.name}"]'
                for null, value in (
                    (nullable, _nullable(column.value)),
                    ("NullT", column.annotation),
                ):
                    self.overload(
                        "select",
                        [
                            (
                                "self",
                                self.joined(
                                    tables, "ColumnT", null, "FieldsT", "StarT"
                                ),
                            ),
                            ("selections", selections),
                        ],
                        self.joined(
                            tables, "ColumnT", null, self.cons(key, value), "StarT"
                        ),
                    )
        self.overload(
            "select",
            [("self", None), ("selections", "ColumnT | Sequence[ColumnT]")],
            self.joined(
                "TablesT", "ColumnT", "NullT", self.cons("str", "object"), "StarT"
            ),
        )
        self.select_impls()
        self.emit(
            ["        # select_as: grouped by value type; the alias becomes a key."]
        )
        for table in model.tables:
            tables = f"TablesT | {table.token}"
            nullable = f"NullT | {table.token}"
            for (value, is_nullable), names in self.by_value(
                table, self.scope_names(table)
            ).items():
                plain = _nullable(value) if is_nullable else value
                for null, read in ((nullable, _nullable(value)), ("NullT", plain)):
                    self.overload(
                        "select_as",
                        [
                            (
                                "self",
                                self.joined(
                                    tables, "ColumnT", null, "FieldsT", "StarT"
                                ),
                            ),
                            ("source", _literal(names)),
                            ("alias", "AliasT"),
                        ],
                        self.joined(
                            tables, "ColumnT", null, self.cons("AliasT", read), "StarT"
                        ),
                    )
        self.overload(
            "select_as",
            [("self", None), ("source", "ColumnT"), ("alias", "str")],
            self.joined(
                "TablesT", "ColumnT", "NullT", self.cons("str", "object"), "StarT"
            ),
        )
        self.emit(
            [
                "        def select_as(self, source: Any, alias: str) -> Any:",
                "            return self._select_as(source, alias)",
                "",
                "        # where: operator families take different value shapes.",
            ]
        )
        for table in model.tables:
            tables = f"TablesT | {table.token}"
            query = self.joined(tables, "ColumnT", "NullT", "FieldsT", "StarT")
            for names, operator, shape in self.shapes(table, self.scope_names(table)):
                self.overload(
                    "where",
                    [
                        ("self", query),
                        ("column", _literal(names)),
                        ("operator", operator),
                        ("value", shape),
                    ],
                    query,
                )
        self.overload(
            "where",
            [
                ("self", None),
                (
                    "column",
                    Sub(
                        "Callable",
                        (
                            Sub("", ("DatabaseExpressionBuilder[TablesT, ColumnT]",)),
                            "Expression[bool]",
                        ),
                    ),
                ),
            ],
            self.joined("TablesT", "ColumnT", "NullT", "FieldsT", "StarT"),
        )
        self.where_impl()
        self.having(
            self.joined("TablesT", "ColumnT", "NullT", "FieldsT", "StarT"),
            "DatabaseExpressionBuilder[TablesT, ColumnT]",
        )
        self.ordering(
            lambda fields: self.joined("TablesT", "ColumnT", "NullT", fields, "StarT"),
            "ColumnT",
        )
        self.emit(
            [
                "        # joins: the ON columns may use the prior scope and the new",
                "        # table. Outer joins record which side may be missing.",
            ]
        )
        for kind in ("inner", "left", "right", "full"):
            for table in model.tables:
                self.overload(
                    f"{kind}_join",
                    [
                        ("self", None),
                        ("table", table.token),
                        ("left", f"ColumnT | {table.scope_alias}"),
                        ("right", f"ColumnT | {table.scope_alias}"),
                    ],
                    self.join_result(
                        kind, table, "TablesT", "ColumnT", "NullT", "StarT"
                    ),
                )
            self.join_impl(kind, "DatabaseQuery")

    def join_result(
        self, kind: str, table: Table, tables: str, columns: str, null: str, star: str
    ) -> Sub:
        marked = f"{null} | {table.token}" if null != "Never" else table.token
        return self.joined(
            f"{tables} | {table.token}",
            f"{columns} | {table.scope_alias}",
            marked if kind in {"left", "full"} else null,
            "FieldsT",
            'Literal["*"]' if kind in {"right", "full"} else star,
        )

    def where_impl(self) -> None:
        self.emit(
            _signature(
                "where",
                [
                    ("self", None),
                    ("column", "Any"),
                    ("operator: Any = None", None),
                    ("value: Any = None", None),
                ],
                "Any",
                8,
                body="",
            )
        )
        self.emit(
            [
                "            if isinstance(column, str):",
                "                name = cast(Any, column)",
                "                return super().where(name, operator, value)",
                "            return super().where(column)",
                "",
            ]
        )

    def join_impl(self, kind: str, cls: str) -> None:
        self.emit(
            [
                f"        def {kind}_join(self, table: Any, left: Any, right: Any)"
                " -> Any:",
                f'            return self._join("{kind}", table, left, right)',
                "",
            ]
        )

    def single_table_base(self) -> None:
        model = self.model
        self.emit(
            [
                "    # Single-table queries. Each table gets its own class so the",
                "    # editor only weighs that table's overloads; joins move to",
                "    # DatabaseQuery.",
                "    class SingleTableQuery(",
                f'        TypedSchemaQueryBuilder["{model.database}", ColumnsT, '
                "FieldsT, Never],",
                "        Generic[TableT, ColumnsT, ScopeT, FieldsT],",
                "    ):",
            ]
        )
        for kind in ("inner", "left", "right", "full"):
            for table in model.tables:
                self.overload(
                    f"{kind}_join",
                    [
                        ("self", None),
                        ("table", table.token),
                        ("left", f"ScopeT | {table.scope_alias}"),
                        ("right", f"ScopeT | {table.scope_alias}"),
                    ],
                    self.join_result(kind, table, "TableT", "ScopeT", "Never", "Never"),
                )
            self.emit(
                [
                    f"        def {kind}_join(self, table: Any, left: Any, right: Any)"
                    " -> Any:",
                    "            query = self._query.join("
                    f'"{kind}", table, left, right)',
                    "            joined: DatabaseQuery[Any, Any, Any, Any, Any] = "
                    "DatabaseQuery(",
                    "                cast(Any, query.typed(DatabaseExpressionBuilder))",
                    "            )",
                    "            return joined",
                    "",
                ]
            )

    def table_query(self, table: Table) -> None:
        model = self.model
        cls = table.query_class
        result = Sub(cls, ("FieldsT",))
        self.emit(
            [
                f"    class {cls}(",
                f"        SingleTableQuery[{table.token}, {table.columns_alias}, "
                f"{table.scope_alias}, FieldsT],",
                "        Generic[FieldsT],",
                "    ):",
            ]
        )
        for column in table.columns:
            self.overload(
                "select",
                [
                    ("self", None),
                    ("selections", _literal(model.spellings(table, column.name))),
                ],
                Sub(cls, (self.cons(f'Literal["{column.name}"]', column.annotation),)),
            )
        self.overload(
            "select",
            [
                ("self", None),
                (
                    "selections",
                    f"{table.columns_alias} | Sequence[{table.columns_alias}]",
                ),
            ],
            Sub(cls, (self.cons("str", "object"),)),
        )
        self.select_impls()
        for (value, is_nullable), names in self.by_value(
            table, self.all_names(table)
        ).items():
            read = _nullable(value) if is_nullable else value
            self.overload(
                "select_as",
                [("self", None), ("source", _literal(names)), ("alias", "AliasT")],
                Sub(cls, (self.cons("AliasT", read),)),
            )
        self.overload(
            "select_as",
            [("self", None), ("source", table.columns_alias), ("alias", "str")],
            Sub(cls, (self.cons("str", "object"),)),
        )
        self.emit(
            [
                "        def select_as(self, source: Any, alias: str) -> Any:",
                "            return self._select_as(source, alias)",
                "",
            ]
        )
        for names, operator, shape in self.shapes(table, self.all_names(table)):
            self.overload(
                "where",
                [
                    ("self", None),
                    ("column", _literal(names)),
                    ("operator", operator),
                    ("value", shape),
                ],
                result,
            )
        builder = f"DatabaseExpressionBuilder[{table.token}, {table.columns_alias}]"
        self.overload(
            "where",
            [
                ("self", None),
                ("column", Sub("Callable", (Sub("", (builder,)), "Expression[bool]"))),
            ],
            result,
        )
        self.where_impl()
        self.having(result, builder)
        self.ordering(lambda fields: Sub(cls, (fields,)), table.columns_alias)


# Pyright stops analysing a module whose top-level code flow exceeds its
# complexity limit; empirically that is about 15,000 function definitions.
PYRIGHT_DEFINITION_CEILING = 14_000


def _expr(source: str) -> ast.expr:
    return ast.parse(source, mode="eval").body


def _args(node: ast.Subscript) -> list[ast.expr]:
    return list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]


class _StubTypes(ast.NodeTransformer):
    def __init__(self, model: SchemaModel, values: list[str]) -> None:
        self.model = model
        self.values = values
        self.group_vars = [f"G{i}" for i in range(len(values))]
        self.current_class = ""
        self.join_table: Table | None = None
        self.projection = False
        self.receiver = False

    def groups(self, table: Table, *, bare: bool = False) -> list[str]:
        result: list[str] = []
        for value in self.values:
            names = [
                name
                for column in table.columns
                if column.value == value
                for name in (
                    self.model.spellings(table, column.name)
                    if bare
                    else self.model.references(table, column.name)
                )
            ]
            result.append(
                "Literal[" + ", ".join(repr(n) for n in names) + "]"
                if names
                else "Never"
            )
        return result

    def fields(self, node: ast.expr) -> list[ast.expr]:
        if isinstance(node, ast.Name) and node.id == "Nil":
            return []
        if isinstance(node, ast.Name) and node.id in {"FieldsT", "RestT"}:
            return [ast.Starred(value=node, ctx=ast.Load())]
        if isinstance(node, ast.Subscript) and ast.unparse(node.value) == "Cons":
            key, value, rest = _args(node)
            return [
                _expr(f"Field[{ast.unparse(key)}, {ast.unparse(value)}]"),
                *self.fields(rest),
            ]
        return [node]

    def visit_Subscript(self, node: ast.Subscript) -> ast.expr:
        name = ast.unparse(node.value)
        args = _args(node)
        if name == "TypedSchemaQueryBuilder":
            _, columns, fields, star = args
            if ast.unparse(star) == "Never":
                star = _expr('Literal[""]')
            return _expr(
                f"QueryCore[{ast.unparse(columns)}, {ast.unparse(star)}, "
                + ", ".join(ast.unparse(f) for f in self.fields(fields))
                + "]"
            )
        if name == "DatabaseExpressionBuilder":
            table = next(
                (
                    t
                    for t in self.model.tables
                    if ast.unparse(args[0]) == ast.unparse(_expr(t.token))
                ),
                None,
            )
            builder_columns = ast.unparse(args[1])
            groups = self.groups(table, bare=True) if table else self.group_vars
            return _expr(
                f"DatabaseExpressionBuilder[{builder_columns}, {', '.join(groups)}]"
            )
        if name == "DatabaseQuery":
            tables, columns, null, fields, star = args
            if self.projection and self.receiver:
                # Do not unpack fields in an explicit scope-checking receiver:
                # mypy can widen tables/nullability when inferring that pack.
                # The non-variadic base checks membership; class-level FieldsT
                # still carries the exact flat selection into the return type.
                return _expr(f"_QueryScope[{ast.unparse(tables)}, {ast.unparse(null)}]")
            if ast.unparse(star) == "Never":
                star = _expr('Literal[""]')
            groups = self.group_vars
            if self.join_table is not None:
                groups = [
                    f"{g} | {new}"
                    for g, new in zip(groups, self.groups(self.join_table), strict=True)
                ]
            args = [
                tables,
                columns,
                null,
                star,
                *[_expr(g) for g in groups],
                *self.fields(fields),
            ]
        elif name == "SingleTableQuery":
            table = next(
                t
                for t in self.model.tables
                if ast.unparse(args[0]) == ast.unparse(_expr(t.token))
            )
            args = [
                *args[:3],
                *[_expr(g) for g in self.groups(table)],
                *self.fields(args[3]),
            ]
        elif name == "Generic":
            args = [f for arg in args for f in self.fields(arg)]
            if self.current_class in {"DatabaseQuery", "SingleTableQuery"}:
                args = (
                    [a for a in args if not isinstance(a, ast.Starred)]
                    + [_expr(g) for g in self.group_vars]
                    + [
                        ast.Starred(
                            value=ast.Name(id="FieldsT", ctx=ast.Load()), ctx=ast.Load()
                        )
                    ]
                )
        elif name in {t.query_class for t in self.model.tables}:
            args = [f for arg in args for f in self.fields(arg)]
        else:
            self.generic_visit(node)
            return node
        node.slice = ast.Tuple(elts=args, ctx=ast.Load())
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.current_class = node.name
        overloaded = {
            n.name
            for n in node.body
            if isinstance(n, ast.FunctionDef)
            and any(ast.unparse(d) == "overload" for d in n.decorator_list)
        }
        query = node.name == "DatabaseQuery" or node.name in {
            t.query_class for t in self.model.tables
        }
        node.body = [
            n
            for n in node.body
            if not (
                isinstance(n, ast.FunctionDef)
                and (
                    (n.name in overloaded and not n.decorator_list)
                    or (query and n.name in {"where", "having"})
                )
            )
        ]
        self.generic_visit(node)
        if query:
            if node.name == "DatabaseQuery":
                columns, groups = "ColumnT", self.group_vars
                node.bases.insert(0, _expr("_QueryScope[TablesT, NullT]"))
            else:
                table = next(t for t in self.model.tables if t.query_class == node.name)
                columns, groups = table.columns_alias, self.groups(table, bare=True)
            builder = f"DatabaseExpressionBuilder[{columns}, {', '.join(groups)}]"
            node.bases.insert(
                0, _expr(f"_Predicates[{builder}, {columns}, {', '.join(groups)}]")
            )
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.projection = node.name in {"select", "select_as"}
        self.receiver = True
        self.visit(node.args)
        self.receiver = False
        if node.name.endswith("_join"):
            annotation = next(a.annotation for a in node.args.args if a.arg == "table")
            assert annotation is not None
            self.join_table = next(
                t
                for t in self.model.tables
                if ast.unparse(_expr(t.token)) == ast.unparse(annotation)
            )
        node.body = [ast.Expr(value=ast.Constant(value=Ellipsis))]
        if node.returns is not None:
            node.returns = self.visit(node.returns)
        self.join_table = None
        self.projection = False
        return node


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
    tree = ast.parse(_Renderer(model).render(source=source_name, output="dbschema.py"))
    nodes: list[ast.stmt] = []
    transform = _StubTypes(model, values)
    for node in tree.body:
        if isinstance(node, ast.If):
            nodes.extend(
                transform.visit(n)
                for n in node.body
                if isinstance(n, ast.ClassDef)
                and n.name not in {"DatabaseExpressionBuilder", "DatabaseClient"}
            )
        elif (
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
        elif isinstance(node, ast.ImportFrom) and node.module == "typing":
            node.names = [
                n for n in node.names if n.name not in {"TYPE_CHECKING", "cast"}
            ]
            nodes.append(node)
        elif isinstance(node, ast.Expr):
            continue
        else:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in {"FieldsT", "RestT"}
                for t in node.targets
            ):
                assert isinstance(node.value, ast.Call)
                node.value.func = ast.Name(id="TypeVarTuple", ctx=ast.Load())
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
        for method in methods:
            if sum(n.name == method.name for n in methods) == 1:
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
            "Codegen only writes .pyi stubs; keep the schema .py handwritten"
        )
    return generate_stub(source, source_name=source_name)
