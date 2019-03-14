from liara.util import add_suffix, flatten_dictionary


def test_flatten_dictionary():
    d = {'a': 1, 'b': {'c': 2}}
    x = flatten_dictionary(d)
    assert x == {'a': 1, 'b.c': 2}


def test_add_suffix():
    import pathlib
    p = pathlib.Path('foo.bar')
    p = add_suffix(p, 'baz')

    assert str(p) == 'foo.baz.bar'
