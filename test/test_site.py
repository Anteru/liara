from liara import site, nodes
from collections import namedtuple
import pathlib
import pytest

item = namedtuple('item', ['metadata', 'name'])


def test_group_recursive():
    items = [
        item({'a': 'key_a_1', 'b': 'key_b_1', 'c': 'key_c_1'}, 1),
        item({'a': 'key_a_1', 'b': 'key_b_1', 'c': 'key_c_1'}, 2),
        item({'a': 'key_a_1', 'b': 'key_b_1', 'c': 'key_c_2'}, 3),
        item({'a': 'key_a_1', 'b': 'key_b_2', 'c': 'key_c_1'}, 4),
        item({'a': 'key_a_1', 'b': 'key_b_1', 'c': 'key_c_1'}, 5),
        item({'a': 'key_a_2', 'b': 'key_b_2', 'c': 'key_c_1'}, 6)
    ]

    groups = site._group_recursive(items, ['a', 'b', 'c'])
    assert len(groups) == 2
    assert 'key_a_1' in groups
    assert 'key_a_2' in groups

    group_1 = groups['key_a_1']
    assert 'key_b_1' in group_1
    assert 'key_b_2' in group_1

    group_1_1 = group_1['key_b_1']
    # c_1 and c_2
    assert len(group_1_1) == 2

    group_1_1_1 = group_1_1['key_c_1']
    # c_1, 1; c_1, 2; c_1, 5
    assert len(group_1_1_1) == 3


def test_group_splat():
    items = [
        item({'tags': ['a', 'b']}, 1),
        item({'tags': ['a', 'c']}, 2),
        item({'tags': ['a', 'd']}, 3),
        item({'tags': ['e', 'b']}, 4),
        item({'tags': ['f', 'b']}, 5),
        item({'tags': ['g', 'b']}, 6)
    ]

    groups = site._group_recursive(items, ['*tags'])
    # 6 tags
    assert len(groups) == 7
    assert len(groups['a']) == 3
    assert items[0] in groups['a']
    assert items[1] in groups['a']
    assert items[2] in groups['a']


class MockDocumentNode(nodes.DocumentNode):
    def __init__(self, path, metadata):
        super().__init__(path, pathlib.PurePosixPath(path))

        self.metadata = metadata


class MockIndexNode(nodes.IndexNode):
    def __init__(self, path):
        super().__init__(pathlib.PurePosixPath(path))


def test_content_filters():
    s = site.Site()
    cff = site.ContentFilterFactory()

    status_filter = cff.create_filter('status')
    s.register_content_filter(status_filter)

    prvn = MockDocumentNode('/private', {'status': 'private'})
    pubn = MockDocumentNode('/public', {})

    s.add_document(pubn)
    s.add_document(prvn)

    assert len(s.nodes) == 1
    assert pathlib.PurePosixPath('/public') in s.urls


class MockObject:
    def __init__(self, metadata):
        self.metadata = metadata


class NestedMockObject:
    def __init__(self, nested):
        self.nested = nested


def test_metadata_accessor():
    n = NestedMockObject({'bar': 23})
    t = MockObject({'o': n})

    c = site._create_metadata_accessor('o.nested.bar')
    assert c(t) == 23


def test_collection():
    n1 = MockDocumentNode('/a', {'title': 'A'})
    n2 = MockDocumentNode('/b', {'title': 'B'})
    n3 = MockDocumentNode('/c', {'title': 'C'})

    root = site.Site()
    root.add_index(MockIndexNode('/'))
    root.add_document(n1)
    root.add_document(n2)
    root.add_document(n3)
    root.create_links()

    collection = site.Collection(root, 'test', '/*')
    nodes = collection.nodes

    assert len(nodes) == 3


def test_collection_group_by_fails_on_missing_metadata():
    n1 = MockDocumentNode('/a', {'title': 'A'})
    n2 = MockDocumentNode('/b', {'title': 'B'})
    n3 = MockDocumentNode('/c', {})

    root = site.Site()
    root.add_index(MockIndexNode('/'))
    root.add_document(n1)
    root.add_document(n2)
    root.add_document(n3)
    root.create_links()

    with pytest.raises(Exception):
        _ = site.Collection(root, 'test', '/*', order_by=['title'])


def test_collection_exclude_without_removes_items():
    n1 = MockDocumentNode('/a', {'title': 'A'})
    n2 = MockDocumentNode('/b', {'title': 'B'})
    n3 = MockDocumentNode('/c', {})

    root = site.Site()
    root.add_index(MockIndexNode('/'))
    root.add_document(n1)
    root.add_document(n2)
    root.add_document(n3)
    root.create_links()

    collection = site.Collection(root, 'test', '/*',
                                 exclude_without=['title'], order_by=['title'])
    nodes = collection.nodes

    assert len(nodes) == 2


def test_index_group_by_fails_on_missing_metadata():
    n1 = MockDocumentNode('/a', {'title': 'A'})
    n2 = MockDocumentNode('/b', {'title': 'B'})
    n3 = MockDocumentNode('/c', {})

    root = site.Site()
    root.add_index(MockIndexNode('/'))
    root.add_document(n1)
    root.add_document(n2)
    root.add_document(n3)
    root.create_links()

    collection = site.Collection(root, 'test', '/*')
    with pytest.raises(Exception):
        _ = site.Index(collection, '/index/%1', group_by=['title'])


def test_index_exclude_without_removes_items():
    n1 = MockDocumentNode('/a', {'year': 2022, 'title': 'A'})
    n2 = MockDocumentNode('/b', {'year': 2022, 'title': 'B'})
    n3 = MockDocumentNode('/c', {'year': 2023})

    root = site.Site()
    root.add_index(MockIndexNode('/'))
    root.add_document(n1)
    root.add_document(n2)
    root.add_document(n3)
    root.create_links()

    collection = site.Collection(root, 'test', '/*')

    index = site.Index(collection, '/index/%1', group_by=['title'],
                       exclude_without=['title'],
                       create_top_level_index=True)
    index.create_nodes(root)

    index_node = root.get_node('/index')
    assert len(index_node.references) == 2


def test_index_exclude_without_key_matching_removes_items():
    n1 = MockDocumentNode('/a', {'year': 2022, 'title': 'A'})
    n2 = MockDocumentNode('/b', {'year': 2022, 'title': 'B'})
    n3 = MockDocumentNode('/c', {'year': 2023, 'title': 'C'})

    root = site.Site()
    root.add_index(MockIndexNode('/'))
    root.add_document(n1)
    root.add_document(n2)
    root.add_document(n3)
    root.create_links()

    collection = site.Collection(root, 'test', '/*')

    index = site.Index(collection, '/index/%1', group_by=['title'],
                       exclude_without=[('year', 2022,)],
                       create_top_level_index=True)
    index.create_nodes(root)

    index_node = root.get_node('/index')
    assert len(index_node.references) == 2
