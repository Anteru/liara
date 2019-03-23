from liara import site, nodes
from collections import namedtuple

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
        nodes.Node.__init__(self)

        self.kind = nodes.NodeKind.Document
        self.metadata = metadata
        self.path = path


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
    assert '/public' in s.urls


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
