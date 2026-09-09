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


def test_base_transformer_covers_write_query_trees():
    db = Pysely[object](dialect=PostgresDialect())
    queries = (
        db.insert_into(users).values({"email": "a@example.com"}),
        db.update_table(users).set({"nickname": "A"}).where(users.c.id.eq(1)),
        db.delete_from(users).where(users.c.id.eq(1)),
    )
    transformer = OperationNodeTransformer()

    assert all(transformer.transform(query._node) == query._node for query in queries)
