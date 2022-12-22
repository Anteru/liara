from liara.nodes import DocumentNode, StaticNode, Node
import pathlib


class MockDocumentNode(DocumentNode):
    def __init__(self, src, metadata):
        super().__init__(src, pathlib.PurePosixPath(src))
        self.metadata = metadata


class MockStaticNode(StaticNode):
    def __init__(self, src):
        super().__init__(src, pathlib.PurePosixPath(src))


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


def test_query_filter_by_kind():
    n1 = MockDocumentNode('/a', {})
    n2 = MockStaticNode('/b')

    root = Node()
    root.path = pathlib.PurePosixPath('/')
    root.add_child(n1)
    root.add_child(n2)

    doc_children = root.select_children().with_node_kinds('document')
    assert len(list(doc_children)) == 1

    static_children = root.select_children().with_node_kinds('static')
    assert len(list(static_children)) == 1

    doc_children = root.select_children().without_node_kinds('static')
    assert len(list(doc_children)) == 1
