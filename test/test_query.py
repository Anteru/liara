# SPDX-FileCopyrightText: 2019 Matthäus G. Chajdas <dev@anteru.net>
# SPDX-License-Identifier: AGPL-3.0-or-later

from liara.nodes import DocumentNode, StaticNode, Node
from liara.template import Page
import pathlib
import pytest


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


def test_query_sort_by_missing_field():
    n1 = MockDocumentNode('/a', {})

    root = Node()
    root.path = pathlib.PurePosixPath('/')
    root.add_child(n1)

    with pytest.raises(Exception):
        list(root.select_children().sorted_by_date())


def test_query_sort_by():
    n1 = MockDocumentNode('/a', {'title': 'A'})
    n2 = MockDocumentNode('/b', {'title': 'B'})

    root = Node()
    root.path = pathlib.PurePosixPath('/')
    root.add_child(n1)
    root.add_child(n2)

    s1 = list(root.select_children().sorted_by_title())
    s2 = list(root.select_children().sorted_by_title(reverse=True))

    assert isinstance(s1[0], Page)
    assert isinstance(s2[1], Page)

    assert s1[0].url == '/a'
    assert s2[1].url == '/a'

    with pytest.raises(Exception):
        _ = list(root.select_children().sorted_by_metadata('non-existant'))

    s3 = list(root.select_children().sorted_by_metadata('title'))
    
    assert isinstance(s3[0], Page)
    assert isinstance(s3[1], Page)

    assert s3[0].url == '/a'
    assert s3[1].url == '/b'


def test_query_limit():
    root = Node()
    root.path = pathlib.PurePosixPath('/')

    for i in range(256):
        root.add_child(MockDocumentNode(f'/{i}', {'title': f'Page {i}'}))

    assert len(list(root.select_children().limit(10))) == 10

def test_query_filter_reversed():
    """Test a query which filters and reverses, but doesn't sort."""
    n1 = MockDocumentNode('/a', {'title': 'A', 'foo': 'bar'})
    n2 = MockDocumentNode('/b', {'title': 'B', 'foo': 'bar'})

    root = Node()
    root.path = pathlib.PurePosixPath('/')
    root.add_child(n1)
    root.add_child(n2)

    s1 = list(root.select_children().with_metadata('foo').reversed())

    assert len(s1) == 2

def test_query_filter_non_string_metadata():
    """Test a query which sort by a non-string entry."""
    n1 = MockDocumentNode('/a', {'title': 'A', 'order': 3})
    n2 = MockDocumentNode('/b', {'title': 'B', 'order': 1})

    root = Node()
    root.path = pathlib.PurePosixPath('/')
    root.add_child(n1)
    root.add_child(n2)

    s1 = list(root.select_children().sorted_by_metadata('order'))

    assert len(s1) == 2

    assert isinstance(s1[0], Page)
    assert s1[0].metadata['title'] == 'B'

def test_query_exclude():
    """Test exclusion by regex."""

    root = Node()
    root.path = pathlib.PurePosixPath('/')
    root.add_child(MockDocumentNode('/aa', {}))
    root.add_child(MockDocumentNode('/ab', {}))
    root.add_child(MockDocumentNode('/bc', {}))

    s1 = list(root.select_children().exclude('a'))

    assert len(s1) == 1

    assert isinstance(s1[0], Page)
    assert s1[0].url == '/bc'

    s2 = list(root.select_children().exclude('b$'))
    assert len(s2) == 2

    s3 = list(root.select_children().exclude('^/a'))
    assert len(s3) == 1
