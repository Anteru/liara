from typing import Dict
from . import Site
from .query import Query
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

    def _match_template(self, url: str) -> str:
        import fnmatch
        matches = []
        for pattern, template in self.__paths.items():
            # Exact matches always win
            if pattern == str(url):
                return template
            # If not exact, we'll look for the longest matching pattern,
            # assuming it is the most specific
            if fnmatch.fnmatch(url, pattern):
                matches.append((len(pattern), template))

        matches = list(sorted(matches, key=lambda x: x[0], reverse=True))
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

    def find_template(self, url) -> Template:
        template = self._match_template(url)
        return MakoTemplate(self.__lookup.get_template(template))


class Jinja2Template(Template):
    def __init__(self, template):
        self.__template = template

    def render(self, **kwargs) -> str:
        return self.__template.render(**kwargs)


class Jinja2TemplateRepository(TemplateRepository):
    def __init__(self, paths: Dict[str, str], path: pathlib.Path):
        super().__init__(paths)
        from jinja2 import FileSystemLoader, Environment

        self.__env = Environment(loader=FileSystemLoader(str(path)))

    def find_template(self, url) -> Template:
        template = self._match_template(url)
        return Jinja2Template(self.__env.get_template(template))


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
        import fnmatch
        nodes = []
        for node in self.__site.nodes:
            if fnmatch.fnmatch(node.path, query):
                nodes.append(node)
        return Query(nodes)
