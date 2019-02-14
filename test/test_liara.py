from liara import flatten_dictionary, match_url


def test_flatten_dictionary():
    d = {'a': 1, 'b': {'c': 2}}
    x = flatten_dictionary(d)
    assert x == {'a': 1, 'b.c': 2}


def test_match_url():
    match, score = match_url('/blog/post/23', '/blog/post/*')
    assert match
    match, score0 = match_url('/blog/post/23', '/blog/post/*')
    assert match
    match, score1 = match_url('/blog/post/235', '/blog/post/*')
    assert match
    assert score0 < score1


def test_match_url_exact():
    match, score = match_url('/blog', '/blog')
    assert match
    assert score == 0


def test_match_fail():
    match, score = match_url('/2014/02/16/2297', '/research/*')
    assert not match
    assert score == -1

    match = match_url('/style.css', '/research/*')
