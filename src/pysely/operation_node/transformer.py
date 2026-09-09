from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import cast

from .nodes import (
    AliasNode,
    AndNode,
    BinaryOperationNode,
    DeleteQueryNode,
    IdentifierNode,
    InsertQueryNode,
    IsNullNode,
    OperationNode,
    OrNode,
    ReferenceNode,
    SelectAllNode,
    SelectQueryNode,
    TableNode,
    UpdateQueryNode,
    ValueNode,
)


class OperationNodeTransformer:
    def transform(self, node: OperationNode) -> OperationNode:
        method = cast(
            Callable[[OperationNode], OperationNode] | None,
            getattr(self, f"transform_{type(node).__name__}", None),
        )
        if method is None:
            raise TypeError(f"Unsupported operation node: {type(node).__name__}")
        return method(node)

    def transform_IdentifierNode(self, node: IdentifierNode) -> OperationNode:
        return node

    def transform_TableNode(self, node: TableNode) -> OperationNode:
        return replace(
            node,
            name=self._identifier(node.name),
            schema=self._optional_identifier(node.schema),
            alias=self._optional_identifier(node.alias),
        )

    def transform_ReferenceNode(self, node: ReferenceNode) -> OperationNode:
        return replace(
            node,
            column=self._identifier(node.column),
            table=tuple(self._identifier(part) for part in node.table),
        )

    def transform_ValueNode(self, node: ValueNode) -> OperationNode:
        return node

    def transform_AliasNode(self, node: AliasNode) -> OperationNode:
        return replace(
            node,
            node=self.transform(node.node),
            alias=self._identifier(node.alias),
        )

    def transform_BinaryOperationNode(self, node: BinaryOperationNode) -> OperationNode:
        return replace(
            node,
            left=self.transform(node.left),
            right=self.transform(node.right),
        )

    def transform_IsNullNode(self, node: IsNullNode) -> OperationNode:
        return replace(node, expression=self.transform(node.expression))

    def transform_AndNode(self, node: AndNode) -> OperationNode:
        return replace(
            node,
            expressions=tuple(self.transform(item) for item in node.expressions),
        )

    def transform_OrNode(self, node: OrNode) -> OperationNode:
        return replace(
            node,
            expressions=tuple(self.transform(item) for item in node.expressions),
        )

    def transform_SelectAllNode(self, node: SelectAllNode) -> OperationNode:
        return replace(
            node,
            table=tuple(self._identifier(part) for part in node.table),
        )

    def transform_SelectQueryNode(self, node: SelectQueryNode) -> OperationNode:
        return replace(
            node,
            from_=tuple(self._table(table) for table in node.from_),
            selections=tuple(self.transform(item) for item in node.selections),
            where=self.transform(node.where) if node.where else None,
        )

    def transform_InsertQueryNode(self, node: InsertQueryNode) -> OperationNode:
        return replace(
            node,
            into=self._table(node.into),
            columns=tuple(self._identifier(column) for column in node.columns),
            values=tuple(
                tuple(self.transform(value) for value in row) for row in node.values
            ),
            returning=tuple(self.transform(item) for item in node.returning),
        )

    def transform_UpdateQueryNode(self, node: UpdateQueryNode) -> OperationNode:
        return replace(
            node,
            table=self._table(node.table),
            assignments=tuple(
                (self._identifier(column), self.transform(value))
                for column, value in node.assignments
            ),
            where=self.transform(node.where) if node.where else None,
            returning=tuple(self.transform(item) for item in node.returning),
        )

    def transform_DeleteQueryNode(self, node: DeleteQueryNode) -> OperationNode:
        return replace(
            node,
            from_=self._table(node.from_),
            where=self.transform(node.where) if node.where else None,
            returning=tuple(self.transform(item) for item in node.returning),
        )

    def _identifier(self, node: IdentifierNode) -> IdentifierNode:
        transformed = self.transform(node)
        if not isinstance(transformed, IdentifierNode):
            raise TypeError("Identifier transforms must return an IdentifierNode")
        return transformed

    def _optional_identifier(
        self, node: IdentifierNode | None
    ) -> IdentifierNode | None:
        return self._identifier(node) if node else None

    def _table(self, node: TableNode) -> TableNode:
        transformed = self.transform(node)
        if not isinstance(transformed, TableNode):
            raise TypeError("Table transforms must return a TableNode")
        return transformed
