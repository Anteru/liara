from liara.nodes import extract_metadata_content
import pytest


def test_extract_toml_metadata():
    document = """+++
a = "b"
+++

content
"""
    metadata, content, first_content_line = extract_metadata_content(document)
    assert 'a' in metadata
    assert metadata['a'] == 'b'
    assert first_content_line == 4
    assert content == """
content
"""


def test_extract_yaml_metadata():
    document = """---
a: "b"
---

content
"""
    metadata, content, first_content_line = extract_metadata_content(document)
    assert 'a' in metadata
    assert metadata['a'] == 'b'
    assert first_content_line == 4
    assert content == """
content
"""


def test_extract_metadata_mismatch_throws():
    document = """---
a = "b"
+++

content
"""

    with pytest.raises(Exception):
        m, c, _ = extract_metadata_content(document)


def test_extract_no_metadata():
    document = """
content
"""

    metadata, content, first_content_line = extract_metadata_content(document)
    assert content == """
content
"""
    assert metadata == {}
    assert first_content_line == 1


def test_extract_metadata_no_trailing_newline():
    document = """---
a: "b"
---"""

    metadata, content, first_content_line = extract_metadata_content(document)
    assert 'a' in metadata
    assert metadata['a'] == 'b'
    assert content == ''
    assert first_content_line == 4
