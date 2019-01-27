import os
import pathlib
from typing import Dict, List, Optional, Any, Iterable, Iterator, Type
from enum import Enum, auto
from contextlib import suppress
import itertools
import multiprocessing
from contextlib import ContextDecorator


class SingleProcessPool(ContextDecorator):
    def map(self, f, iterable):
        return map(f, iterable)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


__version__ = '0.2.0'


def load_yaml(s):
    import yaml
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader
    return yaml.load(s, Loader=Loader)


def dump_yaml(data, stream=None):
    import yaml
    try:
        from yaml import CDumper as Dumper
    except ImportError:
        from yaml import Dumper

    return yaml.dump(data, stream, Dumper=Dumper)


class NodeKind(Enum):
    Resource = auto()
    Index = auto()
    Document = auto()
    Data = auto()
    # Static nodes will not get any processing applied. Metadata can be
    # generated (for instance, image size)
    Static = auto()
    # Nodes can be automatically generated, for instance for redirections
    Generated = auto()


class Node:
    kind: NodeKind
    # Source file path
    src: pathlib.Path
    # Relative path
    path: pathlib.PurePosixPath

    metadata: Dict[str, Any] = {}
    children: List['Node'] = []
    parent: Optional['Node'] = None

    def add_child(self, child: 'Node') -> None:
        self.children.append(child)
        child.parent = self

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.src)})'

    def select_children(self) -> 'Query':
        return Query(self.children)


class SelectionFilter:
    def match(self, node: Node) -> bool:
        pass


class TagFilter(SelectionFilter):
    def __init__(self, name, value=None):
        self.__name = name
        self.__value = value

    def match(self, node: Node) -> bool:
        if self.__name in node.metadata:
            if self.__value is not None:
                return node.metadata[self.__name] == self.__value
            else:
                return True
        return False


class Sorter:
    def get_key(self, item):
        pass


class TitleSorter(Sorter):
    def get_key(self, item: 'Page'):
        return item.meta['title']


class TagSorter(Sorter):
    def __init__(self, tag: str):
        self.__tag = tag

    def get_key(self, item: 'Page'):
        return item.meta.get[self.__tag]


class Query(Iterable[Node]):
    __filters: List[SelectionFilter] = []
    __nodes: List[Node] = []
    __sorters: List[Sorter] = []

    def __init__(self, nodes):
        self.__nodes = nodes

    def with_tag(self, name, value=None) -> 'Query':
        self.__filters.append(TagFilter(name, value))
        return self

    def sorted_by_title(self) -> 'Query':
        self.__sorters.append(TitleSorter())
        return self

    def sorted_by_tag(self, tag: str) -> 'Query':
        self.__sorters.append(TagSorter(tag))
        return self

    def __iter__(self) -> Iterator[Node]:
        nodes = self.__nodes
        for f in self.__filters:
            nodes = filter(lambda x: f.match(x), nodes)
        result = map(Page, nodes)
        if self.__sorters:
            def get_key(item):
                return tuple([s.get_key(item) for s in self.__sorters])
            result = sorted(result, key=get_key)

        return iter(result)


def extract_metadata_content(path: pathlib.Path):
    # We start by expecting a '---', once we find that, we keep reading
    # until we discover another '---'.
    # The states are:
    # 0: Expecting '---'
    # 1: Assembling metadata, expecting '---'
    # 2: Content
    # TODO Use a stream here instead of readlines() to improve reading
    # performance
    state = 0
    metadata = ''
    content = ''

    for line in path.open(encoding='utf-8').readlines():
        if state == 0 and line == '---\n':
            state = 1
        elif state == 1 and line == '---\n':
            state = 2
        elif state == 1 and line != '---\n':
            metadata += line
        elif state == 2:
            content += line

    return load_yaml(metadata), content


class DocumentNode(Node):
    def __init__(self, src, path):
        super().__init__()
        self.kind = NodeKind.Document
        self.src = src
        self.path = path
        self.metadata, self.__raw_content = extract_metadata_content(self.src)

    def validate_metadata(self):
        if 'title' not in self.metadata:
            raise Exception(f"'title' missing for Document: '{self.src}'")

    def validate_links(self, site: 'Site'):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.content, 'lxml')

        def validate_link(link):
            if not link.startswith('/'):
                return

            link = pathlib.PurePosixPath(link)
            if link not in site.urls:
                print(f'"{link}" referenced in "{self.path}" does not exist')

        for link in soup.find_all('a'):
            target = link.attrs.get('href', None)
            validate_link(target)

        for image in soup.find_all('img'):
            target = image.attrs.get('src', None)
            validate_link(target)

    def process_content(self):
        import markdown
        import pymdownx.arithmatex as arithmatex
        from .md import HeadingLevelFixupExtension

        extensions = [
            arithmatex.ArithmatexExtension(),
            HeadingLevelFixupExtension(),
            'fenced_code',
            'codehilite',
            'smarty'
        ]
        extension_configs = {
            'codehilite': {
                'css_class': 'code'
            }
        }
        self.content = markdown.markdown(self.__raw_content,
                                         extensions=extensions,
                                         extension_configs=extension_configs)


class DataNode(Node):
    def __init__(self, src, path):
        super().__init__()
        self.kind = NodeKind.Data
        self.src = src
        self.path = path
        self.metadata = load_yaml(self.src.open('r'))


class IndexNode(Node):
    def __init__(self, path):
        super().__init__()
        self.kind = NodeKind.Index
        self.src = None
        self.path = path


class GeneratedNode(Node):
    def __init__(self, path, metadata={}):
        super().__init__()
        self.kind = NodeKind.Generated
        self.src = None
        self.path = path
        self.metadata = metadata

    def generate(self, output_path: pathlib.Path):
        pass


_REDIRECTION_TEMPLATE = """<!DOCTYPE HTML>
<html lang="en-US">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="0; url={{NEW_URL}}">
        <script type="text/javascript">
            window.location.href = "{{NEW_URL}}"
        </script>
        <title>Page Redirection</title>
    </head>
    <body>
        <h1>Page has been moved</h1>
        <p>If you are not redirected automatically, follow this
        <a href='{{NEW_URL}}'>link.</a>.</p>
    </body>
</html>"""


class RedirectionNode(GeneratedNode):
    def __init__(self, path, dst):
        super().__init__(path)
        self.dst = dst

    def generate(self, output_path: pathlib.Path):
        os.makedirs(output_path, exist_ok=True)
        output_path = output_path / 'index.html'
        text = _REDIRECTION_TEMPLATE.replace('{{NEW_URL}}',
                                             self.dst.as_posix())
        output_path.write_text(text)


class ResourceNode(Node):
    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Resource
        self.src = src
        self.path = path
        if metadata_path:
            self.metadata = load_yaml(open(metadata_path, 'r'))


class SassResourceNode(ResourceNode):
    def __init__(self, src, path, metadata_path=None):
        super().__init__(src, path, metadata_path)
        if src.suffix not in {'.scss', '.sass'}:
            raise Exception("SassResource can be only created for a .scss or "
                            " .sass file")

        self.path = self.path.with_suffix('.css')

    def process_content(self):
        import sass
        self.content = sass.compile(filename=str(self.src)).encode('utf-8')


class ResourceNodeFactory:
    __known_types: Dict[str, Type] = {}

    def __init__(self):
        self.register_type(['.sass', '.scss'], SassResourceNode)

    def register_type(self, suffixes, node_type) -> None:
        if isinstance(suffixes, str):
            suffixes = []

        for suffix in suffixes:
            self.__known_types[suffix] = node_type

    def create_node(self, suffix, src, path, metadata_path=None) \
            -> ResourceNode:
        class_ = self.__known_types[suffix]
        return class_(src, path, metadata_path)


class StaticNode(Node):
    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Static
        self.src = src
        self.path = path
        if metadata_path:
            self.metadata = load_yaml(open(metadata_path, 'r'))

    def update_metadata(self) -> None:
        from PIL import Image
        if self.src.suffix in {'.jpg', '.png'}:
            image = Image.open(self.src)
            self.metadata.update({
                'image_size': image.size
            })


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


class Site:
    data: List[DataNode] = []
    indices: List[IndexNode] = []
    documents: List[DocumentNode] = []
    resources: List[ResourceNode] = []
    static: List[StaticNode] = []
    generated: List[GeneratedNode] = []
    __nodes: Dict[pathlib.PurePosixPath, Node] = {}

    def add_data(self, node: DataNode) -> None:
        self.data.append(node)
        self.__register_node(node)

    def add_index(self, node: IndexNode) -> None:
        self.indices.append(node)
        self.__register_node(node)

    def add_document(self, node: DocumentNode) -> None:
        self.documents.append(node)
        self.__register_node(node)

    def add_resource(self, node: ResourceNode) -> None:
        self.resources.append(node)
        self.__register_node(node)

    def add_static(self, node: StaticNode) -> None:
        self.static.append(node)
        self.__register_node(node)

    def add_generated(self, node: GeneratedNode) -> None:
        self.generated.append(node)
        self.__register_node(node)

    def __register_node(self, node: Node) -> None:
        if node.path in self.__nodes:
            raise Exception(f'"{node.path}" already exists, cannot overwrite.')
        self.__nodes[node.path] = node

    @property
    def nodes(self) -> Iterable[Node]:
        return self.__nodes.values()

    @property
    def urls(self) -> Iterable[pathlib.PurePosixPath]:
        return self.__nodes.keys()

    def create_links(self):
        '''This creates links between parents/children.

        We have to do this in a separate step, as we merge static/resource
        nodes from themes etc.'''
        for key, node in self.__nodes.items():
            parent_path = key.parent
            parent_node = self.__nodes.get(parent_path)
            if parent_node:
                parent_node.add_child(node)


def process_content(obj):
    obj.process_content()
    return obj


def create_default_configuration() -> Dict[str, Any]:
    return {
        'content_directory': 'content',
        'resource_directory': 'resources',
        'static_directory': 'static',
        'output_directory': 'output',
        'build': {
            'clean_output': True,
            'multiprocess': False
        },
        'template': 'templates/default.yaml',
        'routes': {
            'static': 'static_routes.yaml',
            'generated': 'generated_routes.yaml'
        },
        'base_url': 'http://localhost:8000'
    }


__ROOT_PATH = pathlib.PurePosixPath('/')


# Create the path from the full path as discovered during walk
# This turns something like 'directory/foo/bar' into '/foo/bar'
def _create_relative_path(path: pathlib.Path, root: pathlib.Path) \
        -> pathlib.PurePosixPath:
    # Extra check, as with_name would fail on an empty path
    if path == root:
        return __ROOT_PATH

    path = path.relative_to(root)
    return __ROOT_PATH / pathlib.PurePosixPath(path.with_name(path.stem))


class Liara:
    __site: Site = Site()
    __resource_node_factory: ResourceNodeFactory = ResourceNodeFactory()
    __redirections: List[RedirectionNode] = []

    def __init__(self, configuration):
        self.__configuration = create_default_configuration()
        if isinstance(configuration, str):
            self.__configuration.update(load_yaml(open(configuration)))
        else:
            self.__configuration.update(load_yaml(configuration))

        template_configuration = pathlib.Path(self.__configuration['template'])
        self.__setup_template_backend(template_configuration)

    def __setup_template_backend(self, configuration_file: pathlib.Path):
        from .template import Jinja2TemplateRepository, MakoTemplateRepository

        template_path = configuration_file.parent
        configuration = load_yaml(open(configuration_file))

        backend = configuration['backend']
        paths = configuration['paths']

        if backend == 'jinja2':
            self.__template_backend = Jinja2TemplateRepository(
                paths, template_path)
        elif backend == 'mako':
            self.__template_backend = MakoTemplateRepository(
                paths, template_path)
        else:
            raise Exception(f'Unknown template backend: "{backend}"')

        if 'resource_directory' in configuration:
            resource_directory = pathlib.Path(
                configuration['resource_directory'])

            self.__discover_resources(self.__site,
                                      self.__resource_node_factory,
                                      template_path / resource_directory)

        if 'static_directory' in configuration:
            static_directory = pathlib.Path(
                configuration['static_directory'])
            self.__discover_static(self.__site,
                                   template_path / static_directory)

    def __discover_redirections(self, site: Site, static_routes: pathlib.Path):
        if not static_routes.exists():
            return

        routes = load_yaml(static_routes.open())
        for route in routes:
            node = RedirectionNode(
                    pathlib.PurePosixPath(route['src']),
                    pathlib.PurePosixPath(route['dst']))
            self.__redirections.append(node)
            site.add_generated(node)

    def __discover_content(self, site: Site, content_root: pathlib.Path) \
            -> None:
        for (dirpath, _, filenames) in os.walk(content_root):
            directory = pathlib.Path(dirpath)
            # Need to run two passes here: First, we check if an _index file is
            # present in this folder, in which case it's the root of this
            # directory
            # Otherwise, we create a new index node
            node: Node
            for filename in filenames:
                if filename.startswith('_index'):
                    src = pathlib.Path(os.path.join(dirpath, filename))
                    node = DocumentNode(src, _create_relative_path(
                        directory, content_root))
                    site.add_document(node)
                    break
            else:
                node = IndexNode(_create_relative_path(directory,
                                                       content_root))
                site.add_index(node)

            for filename in filenames:
                if filename.startswith('_index'):
                    continue

                src = pathlib.Path(os.path.join(directory, filename))
                path = _create_relative_path(src, content_root)

                if src.suffix in {'.md'}:
                    node = DocumentNode(src, path)
                    site.add_document(node)
                elif src.suffix in {'.yaml'}:
                    node = DataNode(src, path)
                    site.add_data(node)
                else:
                    metadata_path = src.with_suffix('.meta')
                    path = path.with_suffix(''.join(src.suffixes))
                    if metadata_path.exists():
                        node = StaticNode(src, path, metadata_path)
                    else:
                        node = StaticNode(src, path)
                    site.add_static(node)

    def __discover_static(self, site: Site, static_root: pathlib.Path) -> None:
        for dirpath, _, filenames in os.walk(static_root):
            directory = pathlib.Path(dirpath)

            for filename in filenames:
                src = directory / filename
                path = _create_relative_path(src, static_root)
                # We need to re-append the source suffix
                # We can't use .with_suffix, as this will break on paths like
                # a.b.c, where with_suffix('foo') will produce a.b.foo instead
                # of a.b.c.foo
                path = path.parent / (path.name + src.suffix)

                metadata_path = src.with_suffix('.meta')
                if metadata_path.exists():
                    node = StaticNode(src, path, metadata_path)
                else:
                    node = StaticNode(src, path)
                site.add_static(node)

    def __discover_resources(self, site: Site,
                             resource_factory: ResourceNodeFactory,
                             resource_root: pathlib.Path) -> None:
        for dirpath, _, filenames in os.walk(resource_root):
            for filename in filenames:
                src = pathlib.Path(os.path.join(dirpath, filename))
                path = _create_relative_path(src, resource_root)

                metadata_path = src.with_suffix('.meta')
                if metadata_path.exists():
                    node = resource_factory.create_node(src.suffix, src, path,
                                                        metadata_path)
                else:
                    node = resource_factory.create_node(src.suffix, src, path)
                site.add_resource(node)

    def discover_content(self) -> Site:
        configuration = self.__configuration

        content_root = pathlib.Path(configuration['content_directory'])
        self.__discover_content(self.__site, content_root)

        static_root = pathlib.Path(configuration['static_directory'])
        self.__discover_static(self.__site, static_root)

        resource_root = pathlib.Path(configuration['resource_directory'])
        self.__discover_resources(self.__site, self.__resource_node_factory,
                                  resource_root)

        static_routes = pathlib.Path(configuration['routes']['static'])
        self.__discover_redirections(self.__site, static_routes)

        return self.__site

    @property
    def site(self) -> Site:
        return self.__site

    def __create_pool(self):
        if self.__configuration['build']['multiprocess']:
            return multiprocessing.Pool()
        else:
            return SingleProcessPool()

    def build(self):
        from .template import SiteTemplateProxy
        import shutil

        if self.__configuration['build']['clean_output']:
            output_directory = self.__configuration['output_directory']
            if os.path.exists(output_directory):
                shutil.rmtree(output_directory)

        with self.__create_pool() as pool:
            self.discover_content()

            site = self.__site
            site.create_links()

            for document in site.documents:
                document.validate_metadata()

            site.documents = pool.map(process_content, site.documents)

            for resource in site.resources:
                resource.process_content()

            output_path = pathlib.Path(
                self.__configuration['output_directory'])

            for node in itertools.chain(site.documents, site.indices):
                page = Page(node)
                file_path = pathlib.Path(str(output_path) + str(node.path))
                file_path.mkdir(parents=True, exist_ok=True)
                file_path = file_path / 'index.html'

                template = self.__template_backend.find_template(node.path)
                file_path.write_text(template.render(
                    site=SiteTemplateProxy(site),
                    page=page,
                    node=node), encoding='utf-8')

            # Write out resource data
            for node in site.resources:
                file_path = pathlib.Path(str(output_path) + str(node.path))
                os.makedirs(file_path.parent, exist_ok=True)
                file_path.write_bytes(node.content)

            # Symlink static data
            for node in site.static:
                file_path = pathlib.Path(str(output_path) + str(node.path))
                os.makedirs(file_path.parent, exist_ok=True)

                with suppress(FileExistsError):
                    # Symlink requires an absolute path
                    source_path = os.path.abspath(node.src)
                    try:
                        os.symlink(source_path, file_path)
                    # If we can't symlink for some reason (for instance,
                    # Windows does not support symlinks by default, we try to
                    # copy instead.
                    except OSError:
                        shutil.copyfile(source_path, file_path)

            for node in site.generated:
                file_path = pathlib.Path(str(output_path) + str(node.path))
                node.generate(file_path)

            for node in self.__redirections:
                with (output_path / '.htaccess').open('w') as output:
                    for node in self.__redirections:
                        output.write(f'RedirectPermanent {str(node.path)} '
                                     f'{str(node.dst)}\n')
