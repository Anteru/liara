from liara import flatten_dictionary


def test_flatten_dictionary():
    d = {'a': 1, 'b': {'c': 2}}
    x = flatten_dictionary(d)
    assert x == {'a': 1, 'b.c': 2}
