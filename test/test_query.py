from liara.nodes import DocumentNode, NodeKind, Node
import pathlib


class MockDocumentNode(DocumentNode):
    def __init__(self, src, metadata):
        self.kind = NodeKind.Document
        self.metadata = metadata
        self.src = src
        self.path = pathlib.PurePosixPath(src)


def test_query_filter_by_tag():
    n1 = MockDocumentNode('/a', {'tags': {'a', 'b'}})
    n2 = MockDocumentNode('/b', {'tags': {'a', 'c'}})
    root = Node()
    root.path = pathlib.PurePosixPath('/')
    root.add_child(n1)
    root.add_child(n2)

    with_a = list(root.select_children().with_tag('a'))
    with_b = list(root.select_children().with_tag('b'))

    assert len(with_a) == 2
    assert len(with_b) == 1
