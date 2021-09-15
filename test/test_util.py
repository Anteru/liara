from liara.util import add_suffix, flatten_dictionary, pairwise


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
    p = pathlib.Path('foo.bar')
    p = add_suffix(p, 'baz')

    assert str(p) == 'foo.baz.bar'


def test_pairwise():
    assert list(pairwise([1, 2, 3])) == [(1, 2,), (2, 3,)]


def test_pairwise_one_element_list():
    assert list(pairwise([1])) == []


def test_pairwise_empty_list():
    assert list(pairwise([])) == []
