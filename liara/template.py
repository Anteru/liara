from .cache import Cache
import pathlib
from typing import (
    Any,
    Dict,
    Optional,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .query import Query
    from . import Site


def _match_url(url: pathlib.PurePosixPath, pattern: str, site: 'Site') \
        -> Optional[int]:
    """Match an url against a pattern.

    :return: An integer indicating the match score, with 0 being a perfect
             match and higher values being increasingly bad. ``None`` is
             returned if no match was found.
    """
    import fnmatch
    import urllib.parse
    from .nodes import _parse_node_kind
    if '?' in pattern and site:
        pattern, params_str = pattern.split('?')

        node = site.get_node(url)
        assert node
        params = urllib.parse.parse_qs(params_str)

        if kinds := params.get('kind'):
            kinds = {_parse_node_kind(kind) for kind in kinds}

            if node.kind not in kinds:
                return None

    # Exact matches always win
    if pattern == str(url):
        return 0
    # If not exact, we'll look for the longest matching pattern,
    # assuming it is the most specific
    if fnmatch.fnmatch(str(url), pattern):
        # abs is required, if our pattern is /*, and the url we match against
        # is /, then the pattern is longer than the URL
        return abs(len(str(url)) - len(pattern))

    return None


class Template:
    def __init__(self, template_path='<unknown>'):
        self._template_path = template_path

    @property
    def path(self):
        return self._template_path

    def render(self, **kwargs):
        pass


class TemplateRepository:
    def __init__(self, paths: Dict[str, str]):
        self.__paths = paths

    def update_paths(self, paths: Dict[str, str]):
        self.__paths = paths

    def find_template(self, url: pathlib.PurePosixPath, site: 'Site') \
            -> Template:
        pass

    def _match_template(self, url: pathlib.PurePosixPath, site: 'Site') -> str:
        best_match = None
        best_score = None
        longest_matching_pattern_length = -1
        for pattern, template in self.__paths.items():
            score = _match_url(url, pattern, site)
            if score is None:
                continue

            # If the pattern is a better match, we always update
            if best_score is None or score < best_score:
                best_score = score
                best_match = template
                longest_matching_pattern_length = len(pattern)

            # Tie breaker: The longer pattern wins
            if best_score == score:
                if len(pattern) > longest_matching_pattern_length:
                    best_match = template
                    longest_matching_pattern_length = len(pattern)

        if not best_match:
            raise Exception(f'Could not find matching template for path: '
                            f'"{url}"')

        return best_match


class MakoTemplate(Template):
    def __init__(self, template, template_path):
        super().__init__(template_path)
        self.__template = template

    def render(self, **kwargs) -> str:
        return self.__template.render(**kwargs)


class MakoTemplateRepository(TemplateRepository):
    def __init__(self, paths: Dict[str, str], path: pathlib.Path):
        super().__init__(paths)
        from mako.lookup import TemplateLookup
        self.__lookup = TemplateLookup(directories=[str(path)])

    def find_template(self, url: pathlib.PurePosixPath, site: 'Site') \
            -> Template:
        template = self._match_template(url, site)
        return MakoTemplate(self.__lookup.get_template(template), template)


class Jinja2Template(Template):
    def __init__(self, template, template_path):
        super().__init__(template_path)
        self.__template = template

    def render(self, **kwargs) -> str:
        return self.__template.render(**kwargs)


class Jinja2TemplateRepository(TemplateRepository):
    """Jinja2 based template repository."""
    def __init__(self, paths: Dict[str, str], path: pathlib.Path,
                 cache: Optional[Cache] = None, *,
                 options: Optional[Dict[str, Any]] = None):
        super().__init__(paths)
        self.__path = path
        self.__cache = cache
        self.__create_environment(options)

    def __create_environment(self, options: Optional[Dict[str, Any]] = None):
        from jinja2 import FileSystemLoader, Environment, BytecodeCache
        from .util import readtime
        import io

        def sanitize_options(options):
            if not options:
                return dict()

            forbidden_options = {
                'undefined',
                'finalize',
                'loader',
                'bytecode_cache',
                'enable_async'
            }

            return {k: v for k, v in options.items()
                    if k not in forbidden_options}

        class Jinja2BytecodeCache(BytecodeCache):
            def __init__(self, cache: Cache):
                self.__cache = cache

            def clear(self):
                pass

            def load_bytecode(self, bucket):
                key = bucket.key.encode('utf-8')
                if content := self.__cache.get(key):
                    s = io.BytesIO(content)
                    bucket.load_bytecode(s)

            def dump_bytecode(self, bucket):
                key = bucket.key.encode('utf-8')
                s = io.BytesIO()
                bucket.write_bytecode(s)

                # Caches pickle under the hood, and a memoryview cannot be
                # pickled -- we thus convert to bytes here
                self.__cache.put(key, s.getbuffer().tobytes())

        if self.__cache:
            cache = Jinja2BytecodeCache(self.__cache)
        else:
            cache = None

        self.__env = Environment(
            loader=FileSystemLoader(str(self.__path)),
            bytecode_cache=cache,
            **sanitize_options(options))
        self.__env.filters['readtime'] = readtime

    def find_template(self, url: pathlib.PurePosixPath, site: 'Site') \
            -> Template:
        template = self._match_template(url, site)
        return Jinja2Template(self.__env.get_template(template), template)


class Page:
    """A wrapper around :py:class:`~liara.nodes.DocumentNode` and
    :py:class:`~liara.nodes.IndexNode` for use inside templates.

    Templates only get applied to those node types, and the :py:class:`Page`
    class provides convenience accessors while hiding the underlying node from
    template code.
    """
    def __init__(self, node):
        self.__node = node

    @property
    def content(self) -> str:
        """Provides the content of this page.
        """
        return getattr(self.__node, 'content', '')

    @property
    def url(self) -> str:
        """Provides the current path of this page.
        """
        # __node.path is a PosixPath object, but inside a template we want to
        # use a basic string
        return str(self.__node.path)

    @property
    def meta(self) -> Dict[str, Any]:
        """Provides the metadata associated with this page.

        .. deprecated:: 2.1.2
           Use :py:attr:`~liara.template.Page.metadata` instead.
        """
        return self.__node.metadata

    @property
    def metadata(self) -> Dict[str, Any]:
        """Provides the metadata associated with this page.

        .. versionadded:: 2.1.2
        """
        return self.__node.metadata

    @property
    def _node(self):
        return self.__node

    def __str__(self):
        return f'Page({self.url})'

    @property
    def references(self) -> 'Query':
        """Provides the list of referenced nodes by this page.

        This can be only used if the current page is an
        :py:class:`~liara.nodes.IndexNode`, in all other cases this will fail.
        For index nodes, this will return the list of references as a
        :py:class:`~liara.query.Query` instance.
        """

        from .nodes import NodeKind
        from .query import Query
        assert self.__node.kind == NodeKind.Index

        return Query(self.__node.references)

    @property
    def children(self) -> 'Query':
        """Return all child pages of this page, i.e. document and index
        nodes.

        .. versionadded:: 2.4"""
        from .query import Query
        return Query(self.__node.children).with_node_kinds('doc', 'idx')


class SiteTemplateProxy:
    """A wrapper around :py:class:`Site` for use inside templates.
    """
    __site: 'Site'

    def __init__(self, site: 'Site'):
        self.__site = site
        self.__data = {}
        for data in self.__site.data:
            self.__data.update(data.content)

    @property
    def data(self) -> Dict[str, Any]:
        """Get the union of all :py:class:`liara.nodes.DataNode`
        instances in this site.
        """
        return self.__data

    @property
    def metadata(self) -> Dict[str, Any]:
        """Provide access to the metadata of this site.
        """
        return self.__site.metadata

    def select(self, query) -> 'Query':
        """Run a query on this site. Returns any node matching the query.
        """
        from .query import Query
        return Query(self.__site.select(query))

    def select_pages(self, query) -> 'Query':
        """Run a query on this site and return only matching pages, i.e.
        document and index nodes.

        .. versionadded:: 2.4"""
        return self.select(query).with_node_kinds('doc', 'idx')

    def get_page_by_url(self, url) -> Optional[Page]:
        """Return a page by URL. If the page cannot be found, return
        ``None``."""
        node = self.__site.get_node(pathlib.PurePosixPath(url))

        if node:
            return Page(node)
        else:
            return None

    def get_previous_in_collection(self, collection: str, page: Page) \
            -> Optional[Page]:
        """Given a collection and a page, return the previous page in this
        collection or ``None`` if this is the first page.
        """
        previous_node = self.__site.get_previous_in_collection(collection,
                                                               page._node)
        if previous_node:
            return Page(previous_node)
        else:
            return None

    def get_next_in_collection(self, collection: str, page: Page) \
            -> Optional[Page]:
        """Given a collection and a page, return the next page in this
        collection or ``None`` if this is the last page.
        """
        next_node = self.__site.get_next_in_collection(collection, page._node)
        if next_node:
            return Page(next_node)
        else:
            return None

    def get_collection(self, collection: str) -> 'Query':
        """Get a collection in form of a :py:class:`liara.query.Query` for
        further filtering/sorting.
        """
        from .query import Query
        # We need to turn this into a list as nodes is of type dict_values
        # and can't be sorted/reversed otherwise
        return Query(list(self.__site.get_collection(collection).nodes))
