from liara.util import add_suffix, flatten_dictionary, pairwise


def test_flatten_dictionary():
    d = {'a': 1, 'b': {'c': 2}}
    x = flatten_dictionary(d)
    assert x == {'a': 1, 'b.c': 2}


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
