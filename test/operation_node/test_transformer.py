from dataclasses import replace

from pysely import PostgresDialect, Pysely
from pysely.operation_node import IdentifierNode, OperationNodeTransformer
from test.fixtures.generated import users


class RenameEmail(OperationNodeTransformer):
    def transform_IdentifierNode(self, node: IdentifierNode):
        if node.name == "email":
            return replace(node, name="email_address")
        return node


def test_transformer_walks_the_complete_select_tree():
    db = Pysely[object](dialect=PostgresDialect())
    query = db.select_from(users).select(users.c.email).where(users.c.email.eq("a"))

    transformed = RenameEmail().transform(query._node)

    assert transformed != query._node
    assert query.compile().sql.count('"email"') == 2
