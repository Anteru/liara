from typing import Dict
from . import Site, match_url
import pathlib


class Template:
    def render(self, **kwargs):
        pass


class TemplateRepository:
    __definition = Dict[str, str]

    def __init__(self, paths: Dict[str, str]):
        self.__paths = paths

    def update_paths(self, paths: Dict[str, str]):
        self.__paths = paths

    def find_template(self, url: str) -> Template:
        pass

    def _match_template(self, url: str, site: Site) -> str:
        matches = []
        for pattern, template in self.__paths.items():
            match, score = match_url(url, pattern, site)
            if match:
                matches.append((score, template,))

        matches = list(sorted(matches, key=lambda x: x[0]))

        return matches[0][1]


class MakoTemplate(Template):
    def __init__(self, template):
        self.__template = template

    def render(self, **kwargs) -> str:
        return self.__template.render(**kwargs)


class MakoTemplateRepository(TemplateRepository):
    def __init__(self, paths: Dict[str, str], path: pathlib.Path):
        super().__init__(paths)
        from mako.lookup import TemplateLookup
        self.__lookup = TemplateLookup(directories=[str(path)])

    def find_template(self, url, site) -> Template:
        template = self._match_template(url, site)
        return MakoTemplate(self.__lookup.get_template(template))


class Jinja2Template(Template):
    def __init__(self, template):
        self.__template = template

    def render(self, **kwargs) -> str:
        return self.__template.render(**kwargs)


class Jinja2TemplateRepository(TemplateRepository):
    """Jinja2 based template repository.

    This class has extra magic internally to allow it to be pickled/unpickled,
    which is necessary for multiprocessing."""
    def __init__(self, paths: Dict[str, str], path: pathlib.Path):
        from jinja2 import FileSystemLoader, Environment

        super().__init__(paths)
        self.__path = path
        self.__env = Environment(loader=FileSystemLoader(str(self.__path)))

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_Jinja2TemplateRepository__env']
        return state

    def __setstate__(self, state):
        from jinja2 import FileSystemLoader, Environment
        self.__dict__.update(state)
        self.__env = Environment(loader=FileSystemLoader(str(self.__path)))

    def find_template(self, url, site) -> Template:
        template = self._match_template(url, site)
        return Jinja2Template(self.__env.get_template(template))


class Page:
    def __init__(self, node):
        self.__node = node

    @property
    def content(self):
        return self.__node.content

    @property
    def url(self):
        # Path is a PosixPath object, but inside a template we want to use a
        # basic string
        return str(self.__node.path)

    @property
    def meta(self):
        return self.__node.metadata


class SiteTemplateProxy:
    __site: Site

    def __init__(self, site: Site):
        self.__site = site
        self.__data = {}
        for data in self.__site.data:
            self.__data.update(data.metadata)

    @property
    def data(self):
        return self.__data

    def select(self, query):
        from .query import Query
        nodes = []
        # TODO This should split the query into individual path components,
        # and traverse the node tree to perform the match instead of
        # enumerating all nodes and then matching them brute force
        for node in self.__site.nodes:
            match, _ = match_url(node.path, query, self.__site)
            if match:
                nodes.append(node)
        return Query(nodes)
