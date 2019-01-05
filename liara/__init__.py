import os
import yaml
import pathlib
from typing import Dict, List, Optional, Any, Iterable, Iterator
from enum import Enum, auto
from contextlib import suppress
import itertools


class NodeKind(Enum):
    Resource = auto()
    Index = auto()
    Document = auto()
    Data = auto()


class Node:
    kind: NodeKind
    # Source file path
    src: pathlib.Path
    # Relative path
    path: pathlib.Path

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
    def get_key(self, item):
        return item.meta['title']


class TagSorter(Sorter):
    def __init__(self, tag):
        self.__tag = tag

    def get_key(self, item):
        return getattr(item.meta, self.__tag)


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

    def sorted_by_tag(self, tag) -> 'Query':
        self.__sorters.append(TagSorter(tag))
        return self

    def __iter__(self) -> Iterator[Node]:
        nodes = self.__nodes.copy()
        for f in self.__filters:
            nodes = filter(lambda x: f.match(x), nodes)
        result = map(Page, nodes)
        if self.__sorters:
            def get_key(item):
                return tuple([s.get_key(item) for s in self.__sorters])
            result = sorted(result, key=get_key)

        return iter(result)


def ExtractMetadataAndContent(path):
    # We start by expecting a '---', once we find that, we keep reading
    # until we discover another '---'.
    # The states are:
    # 0: Expecting '---'
    # 1: Assembling metadata, expecting '---'
    # 2: Content
    state = 0
    metadata = ''
    content = ''

    for line in open(path, 'r').readlines():
        if state == 0 and line == '---\n':
            state = 1
        elif state == 1 and line == '---\n':
            state = 2
        elif state == 1 and line != '---\n':
            metadata += line
        elif state == 2:
            content += line

    return yaml.load(metadata), content


class DocumentNode(Node):
    def __init__(self, src, path):
        super().__init__()
        self.kind = NodeKind.Document
        self.src = src
        self.path = path
        self.metadata, self.__raw_content = ExtractMetadataAndContent(self.src)

    def validate_metadata(self):
        if 'title' not in self.metadata:
            raise Exception(f"'title' missing for Document: '{self.src}'")

    def process_content(self):
        import markdown
        self.content = markdown.markdown(self.__raw_content)


class DataNode(Node):
    def __init__(self, src, path):
        super().__init__()
        self.kind = NodeKind.Data
        self.src = src
        self.path = path
        self.metadata = yaml.load(self.src.open('r'))


class IndexNode(Node):
    def __init__(self, path):
        super().__init__()
        self.kind = NodeKind.Index
        self.src = None
        self.path = path


class ResourceNode(Node):
    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Resource
        self.src = src
        self.path = path
        if metadata_path:
            self.metadata = yaml.load(open(metadata_path, 'r'))

    def publish(self, output_path) -> None:
        pass


class Content:
    data: List[DataNode] = []
    indices: List[IndexNode] = []
    documents: List[DocumentNode] = []
    resources: List[ResourceNode] = []

    def add_data(self, node: DataNode) -> None:
        self.data.append(node)

    def add_index(self, node: IndexNode) -> None:
        self.indices.append(node)

    def add_document(self, node: DocumentNode) -> None:
        self.documents.append(node)

    def add_resource(self, node: ResourceNode) -> None:
        self.resources.append(node)

    @property
    def nodes(self):
        return self.data + self.indices + self.documents + self.resources

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
    __data: Dict[str, Any] = {}

    def add_data(self, data) -> None:
        self.__data.update(data)

    @property
    def data(self):
        return self.__data


class BuildContext:
    def __init__(self, configuration):
        import yaml
        if isinstance(configuration, str):
            self.__configuration = yaml.load(open(configuration))
        else:
            self.__configuration = yaml.load(configuration)
        self.__setup_template_backend(self.__configuration['templates'])

    def __setup_template_backend(self, configuration):
        from .template import Jinja2TemplateRepository, MakoTemplateRepository

        routes = yaml.load(open(configuration['routes']))

        backend = configuration['backend']
        if backend == 'jinja2':
            self.__template_backend = Jinja2TemplateRepository(
                routes, configuration['path'])
        elif backend == 'mako':
            self.__template_backend = MakoTemplateRepository(
                routes, configuration['path'])
        else:
            raise Exception(f'Unknown template backend: "{backend}"')

    def __discover_content(self, directory) -> Content:
        root = pathlib.Path(directory)
        result = Content()

        # Create the path from the full path as discovered during walk
        # This turns something like 'directory/foo/bar' into '/foo/bar'
        def create_path(path):
            path = pathlib.Path(path)
            # Extra check, as with_name would fail on an empty path
            if path == root:
                return pathlib.PurePosixPath('/')

            path = path.relative_to(root)
            path = pathlib.PurePosixPath('/') \
                / pathlib.PurePosixPath(path.with_name(path.stem))
            return path

        roots = {}
        for(dirpath, _, filenames) in os.walk(directory):
            # Need to run two passes here: First, we check if an _index file is
            # present in this folder, in which case it's the root of this
            # directory
            # Otherwise, we create a new index node
            for filename in filenames:
                if filename.startswith('_index'):
                    src = pathlib.Path(os.path.join(dirpath, filename))
                    node = DocumentNode(src, create_path(dirpath))
                    roots[dirpath] = node
                    result.add_document(node)

                    # For index nodes, we manually walk up to the next parent
                    # This is different from the logic used in the second loop,
                    # as for that loop, the parent is either the index node for
                    # the current folder, or a manually created root
                    parent_path = str(pathlib.Path(dirpath).parent)
                    if parent_path in roots:
                        roots[parent_path].add_child(node)
                    break
            else:
                node = IndexNode(create_path(dirpath))
                roots[dirpath] = node
                result.add_index(node)

                # Same logic as above
                parent_path = str(pathlib.Path(dirpath).parent)
                if parent_path in roots:
                    roots[parent_path].add_child(node)

            for filename in filenames:
                if filename.startswith('_index'):
                    continue

                src = pathlib.Path(os.path.join(dirpath, filename))
                path = create_path(src)

                if src.suffix in {'.md'}:
                    node = DocumentNode(src, path)
                    if dirpath in roots:
                        roots[dirpath].add_child(node)
                    result.add_document(node)
                elif src.suffix in {'.yaml'}:
                    node = DataNode(src, path)
                    result.add_data(node)
                else:
                    metadata_path = src.with_suffix('.meta')
                    path = path.with_suffix(''.join(src.suffixes()))
                    if metadata_path.exists():
                        node = ResourceNode(src, path, metadata_path)
                    else:
                        node = ResourceNode(src, path)
                    result.add_resource(node)

        return result

    def discover_content(self) -> Content:
        return self.__discover_content(
            self.__configuration['content_directory'])

    def build(self):
        content = self.__discover_content(
            self.__configuration['content_directory'])

        for document in content.documents:
            document.validate_metadata()

        for document in content.documents:
            document.process_content()

        site = Site()
        for data in content.data:
            site.add_data(data.metadata)

        output_path = pathlib.Path(self.__configuration['output_directory'])
        for node in itertools.chain(content.documents, content.indices):
            page = Page(node)
            file_path = pathlib.Path(str(output_path) + str(node.path))
            file_path.mkdir(parents=True, exist_ok=True)
            file_path = file_path / 'index.html'

            template = self.__template_backend.find_template(node.path)
            file_path.open('w').write(template.render(
                site=site, page=page, node=node))

        # Symlink static data
        for(dirpath, dirnames, filenames) in os.walk(
                self.__configuration['static_directory']):
            for filename in filenames:
                source_path = pathlib.Path(dirpath) / filename
                output_path = pathlib.Path('output')
                output_path /= source_path.relative_to('static')

                os.makedirs(output_path.parent, exist_ok=True)

                with suppress(FileExistsError):
                    # Symlink requires an absolute path
                    os.symlink(os.path.abspath(source_path), output_path)
