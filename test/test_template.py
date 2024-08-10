import pathlib
from liara.template import Template, _match_url, TemplateRepository
import pytest
import liara.site


@pytest.fixture
def default_site():
    site = liara.site.Site()
    return site


def test_match_url(default_site):
    score0 = _match_url('/blog/post/23', '/blog/post/*', default_site)
    assert score0 is not None
    score1 = _match_url('/blog/post/235', '/blog/post/*', default_site)
    assert score1 is not None
    assert score0 < score1


def test_match_url_exact(default_site):
    score = _match_url('/blog', '/blog', default_site)
    assert score == 0
    score = _match_url('/blog/', '/blog/*', default_site)
    assert score is not None and score > 0


def test_match_fail(default_site):
    score = _match_url('/2014/02/16/2297', '/research/*', default_site)
    assert score is None


def test_match_subfolders(default_site):
    score = _match_url('/research/a/b', '/research/*', default_site)
    assert score is not None


def test_match_url_wildcard(default_site):
    score0 = _match_url('/blog', '/blog*', default_site)
    score1 = _match_url('/blog', '/*', default_site)

    # Both patterns match
    assert score0 is not None
    assert score1 is not None

    # The first pattern is a better match and should have a lower score
    assert score0 < score1


class _MockTemplateRepository(TemplateRepository):
    def find_template(self, url: pathlib.PurePosixPath, site: liara.site.Site) -> Template:
        raise NotImplementedError()


def test_match_url_order_independent(default_site):
    tr0 = _MockTemplateRepository(
        {
            '/*': 'default',
            '/en*': 'en'
        }
    )

    t00 = tr0._match_template(pathlib.PurePosixPath('/en'), default_site)
    assert t00 == 'en'

    t01 = tr0._match_template(pathlib.PurePosixPath('/'), default_site)
    assert t01 == 'default'

    tr1 = _MockTemplateRepository(
        {
            '/en*': 'en',
            '/*': 'default'
        }
    )

    t10 = tr1._match_template(pathlib.PurePosixPath('/en'), default_site)
    assert t10 == 'en'

    t11 = tr1._match_template(pathlib.PurePosixPath('/'), default_site)
    assert t11 == 'default'


def test_match_url_same_length(default_site):
    tr0 = _MockTemplateRepository(
        {
            '/e*': 'a',
            '/*n': 'b'
        }
    )

    t00 = tr0._match_template(pathlib.PurePosixPath('/en'), default_site)
    assert t00 == 'a'

    tr1 = _MockTemplateRepository(
        {
            '/*n': 'a',
            '/e*': 'b'
        }
    )

    t10 = tr1._match_template(pathlib.PurePosixPath('/en'), default_site)
    assert t10 == 'a'
