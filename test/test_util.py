from liara.util import (
    CaseInsensitiveDictionary,

    add_suffix,
    flatten_dictionary,
    pairwise,
    merge_dictionaries,
)
import pytest


def test_flatten_dictionary():
    d = {'a': 1, 'b': {'c': 2}}
    x = flatten_dictionary(d)
    assert x == {'a': 1, 'b.c': 2}


def test_flatten_dictionary_with_ignores():
    d = {'no_flatten': {'a': 1}, 'flatten': {'a': 1}}
    x = flatten_dictionary(d, ignore_keys={'no_flatten'})
    assert x['no_flatten']['a'] == 1
    assert 'flatten.a' in x


def test_flatten_dictionary_with_ignores_nested():
    d = {'no': {'no_flatten': {'a': 1}}, 'flatten': {'a': 1}}
    x = flatten_dictionary(d, ignore_keys={'no.no_flatten'})
    assert x['no.no_flatten']['a'] == 1
    assert 'flatten.a' in x


def test_add_suffix():
    import pathlib
    p = pathlib.PurePosixPath('foo.bar')
    p = add_suffix(p, 'baz')

    assert str(p) == 'foo.baz.bar'


def test_pairwise():
    assert list(pairwise([1, 2, 3])) == [(1, 2,), (2, 3,)]


def test_pairwise_one_element_list():
    assert list(pairwise([1])) == []


def test_pairwise_empty_list():
    assert list(pairwise([])) == []


def test_merge_dictionaries():
    a = {"key0": "value", "key1": {"foo": "bar"}}
    b = {"key0": "other_value", "key1": {"fiz": "bug"}}

    m = merge_dictionaries(a, b)

    r = {"key0": "other_value", "key1": {"foo": "bar", "fiz": "bug"}}
    assert m == r
    assert m == a


def test_merge_dictionaries_fails_with_mismatch():
    a = {"key1": {"foo": {"bar": "baz"}}}
    b = {"key1": {"foo": "bug"}}

    with pytest.raises(RuntimeError):
        merge_dictionaries(a, b)


def test_case_insensitive_dictionary():
    a = CaseInsensitiveDictionary({
        "Foo": 23,
        "bAr": 42
    })

    assert "foo" in a
    assert "bar" in a

    assert "FOO" in a
    assert "BAR" in a

    keys = a.keys()
    assert len(keys) == 2
    assert sorted(keys) == sorted(["Foo", "bAr"])

    assert a["Foo"] == 23
    assert a["bAr"] == 42

    assert a["FOO"] == 23
    assert a["bar"] == 42

    assert len(a) == 2
