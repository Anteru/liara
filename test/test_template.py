from liara.template import _match_url
import pytest
import liara.site


@pytest.fixture
def default_site():
    site = liara.site.Site()
    return site


def test_match_url(default_site):
    match, score0 = _match_url('/blog/post/23', '/blog/post/*', default_site)
    assert match
    match, score1 = _match_url('/blog/post/235', '/blog/post/*', default_site)
    assert match
    assert score0 < score1


def test_match_url_exact(default_site):
    match, score = _match_url('/blog', '/blog', default_site)
    assert match
    assert score == 0
    match, score = _match_url('/blog/', '/blog/*', default_site)
    assert match
    assert score > 0


def test_match_fail(default_site):
    match, score = _match_url('/2014/02/16/2297', '/research/*', default_site)
    assert not match
    assert score == -1
