from __future__ import annotations

from .nodes import (
    AliasNode,
    AndNode,
    BinaryOperationNode,
    IdentifierNode,
    IsNullNode,
    OperationNode,
    ReferenceNode,
    SelectAllNode,
    SelectQueryNode,
    TableNode,
    ValueNode,
)


class OperationNodeVisitor:
    def visit(self, node: OperationNode) -> None:
        method = getattr(self, f"visit_{type(node).__name__}", None)
        if method is None:
            raise TypeError(f"Unsupported operation node: {type(node).__name__}")
        method(node)

    def visit_IdentifierNode(self, node: IdentifierNode) -> None:
        pass

    def visit_TableNode(self, node: TableNode) -> None:
        self.visit(node.name)
        if node.schema:
            self.visit(node.schema)
        if node.alias:
            self.visit(node.alias)

    def visit_ReferenceNode(self, node: ReferenceNode) -> None:
        for part in node.table:
            self.visit(part)
        self.visit(node.column)

    def visit_ValueNode(self, node: ValueNode) -> None:
        pass

    def visit_AliasNode(self, node: AliasNode) -> None:
        self.visit(node.node)
        self.visit(node.alias)

    def visit_BinaryOperationNode(self, node: BinaryOperationNode) -> None:
        self.visit(node.left)
        self.visit(node.right)

    def visit_IsNullNode(self, node: IsNullNode) -> None:
        self.visit(node.expression)

    def visit_AndNode(self, node: AndNode) -> None:
        for expression in node.expressions:
            self.visit(expression)

    def visit_SelectAllNode(self, node: SelectAllNode) -> None:
        for part in node.table:
            self.visit(part)

    def visit_SelectQueryNode(self, node: SelectQueryNode) -> None:
        for table in node.from_:
            self.visit(table)
        for selection in node.selections:
            self.visit(selection)
        if node.where:
            self.visit(node.where)
