import os
import pathlib
from typing import Dict, List, Optional, Any, Iterable, Type, Union
from enum import Enum, auto
from contextlib import suppress, ContextDecorator
import multiprocessing
import itertools
import collections


class SingleProcessPool(ContextDecorator):
    def map(self, f, iterable):
        return list(map(f, iterable))

    def imap_unordered(self, f, iterable):
        return list(map(f, iterable))

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

    metadata: Dict[str, Any]
    children: List['Node']
    parent: Optional['Node']

    def __init__(self):
        self.children = []
        self.metadata = {}
        self.parent = None

    def add_child(self, child: 'Node') -> None:
        self.children.append(child)
        child.parent = self

    def __repr__(self):
        return f'{self.__class__.__name__}({self.path})'

    def select_children(self):
        from .query import Query
        return Query(self.children)


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


def _publish_with_template(output_path: pathlib.Path,
                           node: Union['DocumentNode', 'IndexNode'],
                           site: 'Site',
                           template_repository) -> pathlib.Path:
    from .template import SiteTemplateProxy
    page = Page(node)
    file_path = pathlib.Path(str(output_path) + str(node.path))
    file_path.mkdir(parents=True, exist_ok=True)
    file_path = file_path / 'index.html'

    template = template_repository.find_template(node.path)
    file_path.write_text(template.render(
        site=SiteTemplateProxy(site),
        page=page,
        node=node), encoding='utf-8')

    return file_path


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

    def reload(self):
        self.metadata, self.__raw_content = extract_metadata_content(self.src)

    def process(self):
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

    def publish(self, output_path: pathlib.Path,
                site: 'Site',
                template_repository) -> pathlib.Path:
        return _publish_with_template(output_path, self, site,
                                      template_repository)


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

    def publish(self, output_path: pathlib.Path,
                site: 'Site',
                template_repository) -> pathlib.Path:
        return _publish_with_template(output_path, self, site,
                                      template_repository)


class GeneratedNode(Node):
    def __init__(self, path, metadata={}):
        super().__init__()
        self.kind = NodeKind.Generated
        self.src = None
        self.path = path
        self.metadata = metadata

    def publish(self, output_path: pathlib.Path):
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
        self.content = None
        if metadata_path:
            self.metadata = load_yaml(open(metadata_path, 'r'))

    def process(self) -> None:
        """Process the content.

        After this function call, self.content is populated."""
        pass

    def reload(self) -> None:
        pass

    def publish(self, output_path: pathlib.Path) -> pathlib.Path:
        self.process()
        file_path = pathlib.Path(str(output_path) + str(self.path))
        os.makedirs(file_path.parent, exist_ok=True)
        file_path.write_bytes(self.content)
        return file_path


class SassResourceNode(ResourceNode):
    def __init__(self, src, path, metadata_path=None):
        super().__init__(src, path, metadata_path)
        if src.suffix not in {'.scss', '.sass'}:
            raise Exception("SassResource can be only created for a .scss or "
                            " .sass file")

        self.path = self.path.with_suffix('.css')

    def reload(self) -> None:
        self.content = None

    def process(self):
        import sass
        if self.content is None:
            self.content = sass.compile(filename=str(self.src)).encode('utf-8')


class ResourceNodeFactory:
    __known_types: Dict[str, Type] = {}

    def __init__(self):
        self.register_type(['.sass', '.scss'], SassResourceNode)

    def register_type(self, suffixes, node_type) -> None:
        if isinstance(suffixes, str):
            suffixes = [suffixes]

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

    def publish(self, output_path: pathlib.Path) -> pathlib.Path:
        import shutil
        file_path = pathlib.Path(str(output_path) + str(self.path))
        os.makedirs(file_path.parent, exist_ok=True)

        with suppress(FileExistsError):
            # Symlink requires an absolute path
            source_path = os.path.abspath(self.src)
            try:
                os.symlink(source_path, file_path)
            # If we can't symlink for some reason (for instance,
            # Windows does not support symlinks by default, we try to
            # copy instead.
            except OSError:
                shutil.copyfile(source_path, file_path)

        return file_path


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

    def get_node(self, path: pathlib.PurePosixPath) -> Optional[Node]:
        return self.__nodes.get(path)


def process_content(obj):
    obj.process()
    return obj


def publish(node, path):
    node.publish(path)


def create_default_configuration() -> Dict[str, Any]:
    return {
        'content_directory': 'content',
        'resource_directory': 'resources',
        'static_directory': 'static',
        'output_directory': 'output',
        'build': {
            'clean_output': True,
            'multiprocess': True
        },
        'template': 'templates/default.yaml',
        'routes': {
            'static': 'static_routes.yaml',
            'generated': 'generated_routes.yaml'
        },
        'base_url': 'http://localhost:8000'
    }


def flatten_dictionary(d, sep='.', parent_key=None):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.Mapping):
            items.extend(flatten_dictionary(v, sep=sep,
                                            parent_key=new_key).items())
        else:
            items.append((new_key, v,))
    return dict(items)


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
        default_configuration = create_default_configuration()
        if isinstance(configuration, str):
            project_configuration = load_yaml(open(configuration))
        else:
            project_configuration = load_yaml(configuration)
        self.__configuration = collections.ChainMap(
            flatten_dictionary(project_configuration),
            flatten_dictionary(default_configuration))

        template_configuration = pathlib.Path(self.__configuration['template'])
        self.__setup_template_backend(template_configuration)

    def _reload_template_paths(self):
        template_configuration = pathlib.Path(self.__configuration['template'])
        configuration = load_yaml(template_configuration.open())
        self.__template_repository.update_paths(configuration['paths'])

    def __setup_template_backend(self, configuration_file: pathlib.Path):
        from .template import Jinja2TemplateRepository, MakoTemplateRepository

        template_path = configuration_file.parent
        configuration = load_yaml(open(configuration_file))

        backend = configuration['backend']
        paths = configuration['paths']

        if backend == 'jinja2':
            self.__template_repository = Jinja2TemplateRepository(
                paths, template_path)
        elif backend == 'mako':
            self.__template_repository = MakoTemplateRepository(
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

        static_routes = pathlib.Path(configuration['routes.static'])
        self.__discover_redirections(self.__site, static_routes)

        return self.__site

    @property
    def site(self) -> Site:
        return self.__site

    def __create_pool(self):
        if self.__configuration['build.multiprocess']:
            return multiprocessing.Pool()
        else:
            return SingleProcessPool()

    def __clean_output(self):
        import shutil
        output_directory = self.__configuration['output_directory']
        if os.path.exists(output_directory):
            shutil.rmtree(output_directory)

    def build(self):
        if self.__configuration['build.clean_output']:
            self.__clean_output()

        with self.__create_pool() as pool:
            self.discover_content()

            site = self.__site
            site.create_links()

            for document in site.documents:
                document.validate_metadata()

            for document in site.documents:
                document.process()

            output_path = pathlib.Path(
                self.__configuration['output_directory'])

            for node in site.documents:
                node.publish(output_path, site, self.__template_repository)

            for node in site.indices:
                node.publish(output_path, site, self.__template_repository)

            print(f'Publishing {len(site.resources)} resource(s)')
            pool.starmap(publish, zip(site.resources,
                                      itertools.repeat(output_path)))
            print(f'Publishing {len(site.static)} static file(s)')
            pool.starmap(publish, zip(site.static,
                                      itertools.repeat(output_path)))
            print(f'Publishing {len(site.generated)} generated file(s)')
            pool.starmap(publish, zip(site.generated,
                                      itertools.repeat(output_path)))

            with (output_path / '.htaccess').open('w') as output:
                for node in self.__redirections:
                    output.write(f'RedirectPermanent {str(node.path)} '
                                 f'{str(node.dst)}\n')

    def _build_single_node(self, path: pathlib.PurePosixPath):
        """Build a single node.

        This is used for just-in-time page generation. Based on a request, a
        single node is built. Special rules apply to make sure this is
        useful for actual work -- for instance, document/resource nodes
        are always rebuilt from scratch, and for documents, we also reload
        all templates."""
        from collections import namedtuple
        result = namedtuple('BuildResult', ['path', 'cache'])
        node = self.__site.get_node(path)
        output_path = pathlib.Path(
            self.__configuration['output_directory'])

        if node is None:
            print(f'Node not found for path: "{path}"')

        # We always regenerate the content
        if node.kind in {NodeKind.Document, NodeKind.Resource}:
            node.reload()
            node.process()
            cache = False
        else:
            cache = True

        if node.kind == NodeKind.Document:
            self._reload_template_paths()
            return result(node.publish(output_path, self.__site,
                                       self.__template_repository),
                          cache)
        else:
            return result(node.publish(output_path), cache)

    def serve(self):
        """Serve the page.

        This does not build the whole page up-front, but rather serves each
        node individually just-in-time, making it very fast to start."""
        import http.server
        if self.__configuration['build.clean_output']:
            self.__clean_output()

        self.discover_content()

        site = self.__site
        site.create_links()

        for document in site.documents:
            document.validate_metadata()

        class RequestHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                path = pathlib.PurePosixPath(self.path)
                if path not in self.server.cache:
                    node_path, cache = \
                        self.server.liara._build_single_node(path)

                    if cache:
                        self.server.cache[path] = node_path
                else:
                    node_path = self.server.cache[path]

                self.send_response(200)
                self.end_headers()
                self.wfile.write(node_path.open('rb').read())

        server_address = ('', 8080)
        httpd = http.server.HTTPServer(server_address,
                                       RequestHandler)
        httpd.liara = self
        httpd.cache = {}
        print('Listening: http://127.0.0.1:8080')
        httpd.serve_forever()
