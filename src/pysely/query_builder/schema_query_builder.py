from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Generic, Literal, Self, TypeAlias, TypeVar, cast
from uuid import uuid4

from pysely.errors import InvalidQueryError, NoResultError
from pysely.expression import Expression
from pysely.operation_node import (
    AndNode,
    BinaryOperationNode,
    JoinKind,
    JoinNode,
    NotNode,
    OrderByItemNode,
    OrNode,
    SelectQueryNode,
    SetOperationNode,
)
from pysely.query_compiler import CompiledQuery
from pysely.query_executor import QueryExecutor
from pysely.schema import Schema, table_node

DatabaseT = TypeVar("DatabaseT")
ScopeT = TypeVar("ScopeT")
ColumnsT = TypeVar("ColumnsT", bound=str)
RowT = TypeVar("RowT")
SchemaComparisonOperator: TypeAlias = Literal[
    "=",
    "!=",
    "<>",
    "<",
    "<=",
    ">",
    ">=",
    "is",
    "is not",
    "like",
    "not like",
    "in",
    "not in",
]
ReferenceOperator: TypeAlias = Literal["=", "!=", "<>", "<", "<=", ">", ">="]
OrderDirection: TypeAlias = Literal["asc", "desc"]
SetOperator: TypeAlias = Literal["union", "union all", "intersect", "except"]


@dataclass(frozen=True)
class ExpressionBuilder(Generic[ColumnsT]):
    """Builds predicates inside a ``where`` callback.

    A generated schema subclasses this with column-aware overloads for
    ``__call__``, so the same scope rules apply inside callbacks as in a flat
    ``where`` call.
    """

    _schema: Schema
    _scope: dict[str, str]

    def __call__(
        self, column: ColumnsT, operator: SchemaComparisonOperator, value: object
    ) -> Expression[bool]:
        return Expression(self._schema.predicate(self._scope, column, operator, value))

    def ref(
        self, left: ColumnsT, operator: ReferenceOperator, right: ColumnsT
    ) -> Expression[bool]:
        return Expression(
            BinaryOperationNode(
                self._schema.reference(self._scope, left),
                operator,
                self._schema.reference(self._scope, right),
            )
        )

    def and_(self, *expressions: Expression[bool]) -> Expression[bool]:
        if not expressions:
            raise ValueError("and_() requires at least one expression")
        return Expression(AndNode(tuple(expression.node for expression in expressions)))

    def or_(self, *expressions: Expression[bool]) -> Expression[bool]:
        if not expressions:
            raise ValueError("or_() requires at least one expression")
        return Expression(OrNode(tuple(expression.node for expression in expressions)))

    def not_(self, expression: Expression[bool]) -> Expression[bool]:
        return Expression(NotNode(expression.node))


ExpressionCallback: TypeAlias = Callable[[ExpressionBuilder[Any]], Expression[bool]]


@dataclass(frozen=True)
class SchemaQueryBuilder(Generic[DatabaseT, ScopeT, RowT]):
    _node: SelectQueryNode
    _executor: QueryExecutor
    _schema: Schema
    _scope: dict[str, str]
    _query_id: str

    @classmethod
    def from_name(cls, name: str, executor: QueryExecutor, schema: Schema) -> Self:
        return cls(
            SelectQueryNode(from_=(table_node(name),)),
            executor,
            schema,
            schema.add_table({}, name),
            uuid4().hex,
        )

    def _builder(self, scope: dict[str, str]) -> ExpressionBuilder[Any]:
        return ExpressionBuilder(self._schema, scope)

    def select(
        self, selections: str | Sequence[str]
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        names = (selections,) if isinstance(selections, str) else tuple(selections)
        nodes = tuple(self._schema.selection(self._scope, name) for name in names)
        return replace(
            self, _node=replace(self._node, selections=(*self._node.selections, *nodes))
        )

    def select_as(
        self, source: str, alias: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        node = self._schema.aliased_selection(self._scope, source, alias)
        return replace(
            self, _node=replace(self._node, selections=(*self._node.selections, node))
        )

    def where(
        self,
        column: str | ExpressionCallback,
        operator: SchemaComparisonOperator | None = None,
        value: object = None,
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        if callable(column):
            predicate = column(self._builder(self._scope)).node
        else:
            if operator is None:
                raise TypeError("where() requires an operator and value")
            predicate = self._schema.predicate(self._scope, column, operator, value)
        where = (
            AndNode((self._node.where, predicate)) if self._node.where else predicate
        )
        return replace(self, _node=replace(self._node, where=where))

    def where_ref(
        self, left: str, operator: ReferenceOperator, right: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        predicate = BinaryOperationNode(
            self._schema.reference(self._scope, left),
            operator,
            self._schema.reference(self._scope, right),
        )
        where = (
            AndNode((self._node.where, predicate)) if self._node.where else predicate
        )
        return replace(self, _node=replace(self._node, where=where))

    def group_by(
        self, columns: str | Sequence[str]
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        names = (columns,) if isinstance(columns, str) else tuple(columns)
        nodes = tuple(self._schema.reference(self._scope, name) for name in names)
        return replace(
            self, _node=replace(self._node, group_by=(*self._node.group_by, *nodes))
        )

    def having(
        self,
        column: str | ExpressionCallback,
        operator: SchemaComparisonOperator | None = None,
        value: object = None,
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        if callable(column):
            predicate = column(self._builder(self._scope)).node
        else:
            if operator is None:
                raise TypeError("having() requires an operator and value")
            predicate = self._schema.predicate(self._scope, column, operator, value)
        having = (
            AndNode((self._node.having, predicate)) if self._node.having else predicate
        )
        return replace(self, _node=replace(self._node, having=having))

    def order_by(
        self, column: str, direction: OrderDirection = "asc"
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        if direction not in {"asc", "desc"}:
            raise InvalidQueryError(f"Unsupported order direction: {direction}")
        expression = self._schema.order_reference(
            self._scope, self._node.selections, column
        )
        item = OrderByItemNode(expression, direction)
        return replace(
            self, _node=replace(self._node, order_by=(*self._node.order_by, item))
        )

    def limit(self, count: int) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        if count < 0:
            raise InvalidQueryError("limit() takes a non-negative integer")
        return replace(self, _node=replace(self._node, limit=count))

    def offset(self, count: int) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        if count < 0:
            raise InvalidQueryError("offset() takes a non-negative integer")
        return replace(self, _node=replace(self._node, offset=count))

    def set_operation(
        self, operator: SetOperator, other: SchemaQueryBuilder[Any, Any, Any]
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        """Append ``union``/``intersect``/``except`` with another select."""
        if len(other._node.selections) != len(self._node.selections):
            raise InvalidQueryError(
                f"{operator} requires the same number of selected columns"
            )
        operation = SetOperationNode(operator, other._node)
        return replace(
            self,
            _node=replace(
                self._node, set_operations=(*self._node.set_operations, operation)
            ),
        )

    def join(
        self, kind: JoinKind, table: str, left: str, right: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        scope = self._schema.add_table(self._scope, table)
        on = BinaryOperationNode(
            self._schema.reference(scope, left),
            "=",
            self._schema.reference(scope, right),
        )
        join = JoinNode(table_node(table), on, kind)
        return replace(
            self,
            _scope=scope,
            _node=replace(self._node, joins=(*self._node.joins, join)),
        )

    def inner_join(
        self, table: str, left: str, right: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        return self.join("inner", table, left, right)

    def left_join(
        self, table: str, left: str, right: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        return self.join("left", table, left, right)

    def right_join(
        self, table: str, left: str, right: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        return self.join("right", table, left, right)

    def full_join(
        self, table: str, left: str, right: str
    ) -> SchemaQueryBuilder[DatabaseT, ScopeT, RowT]:
        return self.join("full", table, left, right)

    def compile(self) -> CompiledQuery[RowT]:
        return cast(
            CompiledQuery[RowT],
            self._executor.compile_query(self._node, self._query_id),
        )

    async def execute(self) -> list[RowT]:
        result = await self._executor.execute_query(self._node, self._query_id)
        return cast(list[RowT], list(result.rows))

    async def execute_take_first(self) -> RowT | None:
        rows = await self.execute()
        return rows[0] if rows else None

    async def execute_take_first_or_throw(self) -> RowT:
        row = await self.execute_take_first()
        if row is None:
            raise NoResultError("Query returned no rows")
        return row
