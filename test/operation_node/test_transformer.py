from dataclasses import replace

from pysely import Pysely, or_
from pysely.operation_node import IdentifierNode, OperationNodeTransformer
from test.fixtures.dialects import postgres_dialect
from test.fixtures.generated import users


class RenameEmail(OperationNodeTransformer):
    def transform_IdentifierNode(self, node: IdentifierNode):
        if node.name == "email":
            return replace(node, name="email_address")
        return node


def test_transformer_walks_the_complete_select_tree():
    db = Pysely[object](dialect=postgres_dialect())
    query = (
        db.select_from(users)
        .select(users.c.email)
        .where(or_(users.c.email.eq("a"), users.c.email.eq("b")))
    )

    transformed = RenameEmail().transform(query._node)

    assert transformed != query._node
    assert query.compile().sql.count('"email"') == 3


def test_base_transformer_covers_write_query_trees():
    db = Pysely[object](dialect=postgres_dialect())
    queries = (
        db.insert_into(users).values({"email": "a@example.com"}),
        db.update_table(users).set({"nickname": "A"}).where(users.c.id.eq(1)),
        db.delete_from(users).where(users.c.id.eq(1)),
    )
    transformer = OperationNodeTransformer()

    assert all(transformer.transform(query._node) == query._node for query in queries)
