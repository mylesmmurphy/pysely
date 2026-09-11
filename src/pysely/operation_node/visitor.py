from __future__ import annotations

from .nodes import (
    AliasNode,
    AndNode,
    BinaryOperationNode,
    DeleteQueryNode,
    IdentifierNode,
    InsertQueryNode,
    IsNullNode,
    JoinNode,
    NotNode,
    OperationNode,
    OrNode,
    ReferenceNode,
    SelectAllNode,
    SelectQueryNode,
    TableNode,
    UpdateQueryNode,
    ValueListNode,
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

    def visit_ValueListNode(self, node: ValueListNode) -> None:
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

    def visit_OrNode(self, node: OrNode) -> None:
        for expression in node.expressions:
            self.visit(expression)

    def visit_NotNode(self, node: NotNode) -> None:
        self.visit(node.expression)

    def visit_SelectAllNode(self, node: SelectAllNode) -> None:
        for part in node.table:
            self.visit(part)

    def visit_SelectQueryNode(self, node: SelectQueryNode) -> None:
        for table in node.from_:
            self.visit(table)
        for join in node.joins:
            self.visit(join)
        for selection in node.selections:
            self.visit(selection)
        if node.where:
            self.visit(node.where)

    def visit_JoinNode(self, node: JoinNode) -> None:
        self.visit(node.table)
        self.visit(node.on)

    def visit_InsertQueryNode(self, node: InsertQueryNode) -> None:
        self.visit(node.into)
        for column in node.columns:
            self.visit(column)
        for row in node.values:
            for value in row:
                self.visit(value)
        for selection in node.returning:
            self.visit(selection)

    def visit_UpdateQueryNode(self, node: UpdateQueryNode) -> None:
        self.visit(node.table)
        for column, value in node.assignments:
            self.visit(column)
            self.visit(value)
        if node.where:
            self.visit(node.where)
        for selection in node.returning:
            self.visit(selection)

    def visit_DeleteQueryNode(self, node: DeleteQueryNode) -> None:
        self.visit(node.from_)
        if node.where:
            self.visit(node.where)
        for selection in node.returning:
            self.visit(selection)
