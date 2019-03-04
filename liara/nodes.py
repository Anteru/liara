from enum import auto, Enum
import pathlib
from .yaml import load_yaml
import toml
from .cache import Cache
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
)
import re


T = TypeVar('T')


class Publisher:
    def publish_document(self, document: 'DocumentNode'):
        pass

    def publish_index(self, index: 'IndexNode'):
        pass

    def publish_resource(self, resource: 'ResourceNode'):
        pass

    def publish_static(self, static: 'StaticNode'):
        pass

    def publish_generated(self, generated: 'GeneratedNode'):
        pass


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
    parent: Optional['Node']
    __nodes: Dict[str, 'Node']

    @property
    def children(self):
        return self.__nodes.values()

    def __init__(self):
        self.__nodes = {}
        self.metadata = {}
        self.parent = None

    def add_child(self, child: 'Node') -> None:
        assert self.path != child.path
        name = child.path.relative_to(self.path).parts[0]
        self.__nodes[name] = child
        child.parent = self

    def __repr__(self):
        return f'{self.__class__.__name__}({self.path})'

    def select_children(self):
        from .query import Query
        return Query(self.children)

    def get_child(self, name) -> Optional['Node']:
        return self.__nodes.get(name)

    def get_children(self, *, recursive=False):
        for child in self.children:
            yield child
            if recursive:
                yield from child.get_children(recursive=True)


_metadata_marker = re.compile(r'(---|\+\+\+)\n')


class MetadataKind(Enum):
    Unknown = auto()
    Yaml = auto()
    Toml = auto()


def extract_metadata_content(path: pathlib.Path):
    text = path.read_text(encoding='utf-8')

    meta_start, meta_end = 0, 0
    content_start, content_end = 0, 0
    metadata_kind = MetadataKind.Unknown

    for match in _metadata_marker.finditer(text):
        if meta_start == 0:
            if match.group() == '---\n':
                metadata_kind = MetadataKind.Yaml
            elif match.group() == '+++\n':
                metadata_kind = MetadataKind.Toml
            meta_start = match.span()[1]
        elif meta_end == 0:
            if match.group() == '---\n':
                if metadata_kind != MetadataKind.Yaml:
                    raise Exception('Metadata markers mismatch -- started '
                                    'with "---", but ended with "+++"')
            elif match.group() == '+++\n':
                if metadata_kind != MetadataKind.Toml:
                    raise Exception('Metadata markers mismatch -- started '
                                    'with "+++", but ended with "---"')

            meta_end = match.span()[0]
            content_start = match.span()[1]
            content_end = len(text)
            break

    if metadata_kind == MetadataKind.Yaml:
        metadata = load_yaml(text[meta_start:meta_end])
    elif metadata_kind == MetadataKind.Toml:
        metadata = toml.load(text[meta_start:meta_end])
    else:
        # We didn't find any metadata here
        metadata = None

    content = text[content_start:content_end]
    return metadata, content


class DocumentNode(Node):
    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Document
        self.src = src
        self.path = path
        self.metadata_path = metadata_path
        self.content = None
        self.__load()

    def validate_metadata(self):
        if self.metadata is None:
            raise Exception(f"No metadata for document: '{self.src}'")
        if 'title' not in self.metadata:
            raise Exception(f"'title' missing for Document: '{self.src}'")

    def _fixup_relative_links(self):
        # early out if there's no relative link in here, as the parsing is
        # very expensive
        if "href=\"." not in self.content:
            return

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.content, 'lxml')

        def is_relative_url(s):
            return s and s[0] == '.'

        for link in soup.find_all('a', {'href': is_relative_url}):
            target = link.attrs.get('href')
            link.attrs['href'] = \
                str(self.path.parent / pathlib.PurePosixPath(target))

        self.content = str(soup)

    def __load(self):
        if self.metadata_path:
            self.metadata = load_yaml(self.metadata_path.read_text())
            self._raw_content = self.src.read_text('utf-8')
        else:
            self.metadata, self._raw_content = \
                extract_metadata_content(self.src)

    def reload(self):
        self.__load()

    def publish(self, publisher: Publisher) -> pathlib.Path:
        return publisher.publish_document(self)


class HtmlDocumentNode(DocumentNode):
    def process(self, cache: Cache):
        self.content = self._raw_content
        self._fixup_relative_links()

        return self


class MarkdownDocumentNode(DocumentNode):
    def process(self, cache: Cache):
        import markdown
        from .md import HeadingLevelFixupExtension
        import hashlib

        byte_content = self._raw_content.encode('utf-8')
        content_hash = hashlib.sha256(byte_content).digest()
        if cache.contains(content_hash):
            self.content = cache.get(content_hash)
            return

        extensions = [
            'pymdownx.arithmatex',
            HeadingLevelFixupExtension(),
            'fenced_code',
            'codehilite',
            'smarty',
            'tables',
            'admonition'
        ]
        extension_configs = {
            'codehilite': {
                'css_class': 'code'
            },
            'pymdownx.arithmatex': {
                'generic': True
            }
        }
        self.content = markdown.markdown(self._raw_content,
                                         extensions=extensions,
                                         extension_configs=extension_configs)
        self._fixup_relative_links()
        cache.put(content_hash, self.content)
        return self


class DataNode(Node):
    def __init__(self, src, path):
        super().__init__()
        self.kind = NodeKind.Data
        self.src = src
        self.path = path
        self.metadata = load_yaml(self.src.open('r'))


class IndexNode(Node):
    # Stores all nodes referenced by this index, which allows linking to
    # children which are not direct descendants
    references: List[Node]

    def __init__(self, path, metadata={}):
        super().__init__()
        self.kind = NodeKind.Index
        self.src = None
        self.path = path
        self.metadata = metadata
        self.references = []

    def add_reference(self, node):
        self.references.append(node)

    def publish(self, publisher) -> pathlib.Path:
        return publisher.publish_index(self)


class GeneratedNode(Node):
    def __init__(self, path, metadata={}):
        super().__init__()
        self.kind = NodeKind.Generated
        self.src = None
        self.path = path
        self.metadata = metadata

    def publish(self, publisher: Publisher):
        return publisher.publish_generated(self)


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

    def generate(self):
        text = _REDIRECTION_TEMPLATE.replace('{{NEW_URL}}',
                                             self.dst.as_posix())
        self.content = text

    def publish(self, publisher: Publisher):
        self.generate()
        publisher.publish_generated(self)


class ResourceNode(Node):
    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Resource
        self.src = src
        self.path = path
        self.content = None
        if metadata_path:
            self.metadata = load_yaml(open(metadata_path, 'r'))

    def process(self, cache: Cache) -> None:
        """Process the content.

        After this function call, self.content is populated."""
        pass

    def reload(self) -> None:
        pass

    def publish(self, publisher: Publisher) -> pathlib.Path:
        return publisher.publish_resource(self)


class SassResourceNode(ResourceNode):
    def __init__(self, src, path, metadata_path=None):
        super().__init__(src, path, metadata_path)
        if src.suffix not in {'.scss', '.sass'}:
            raise Exception("SassResource can be only created for a .scss or "
                            " .sass file")

        self.path = self.path.with_suffix('.css')

    def reload(self) -> None:
        self.content = None

    def process(self, cache: Cache):
        import sass
        if self.content is None:
            self.content = sass.compile(filename=str(self.src)).encode('utf-8')
        return self


class NodeFactory(Generic[T]):
    __known_types: Dict[str, Type]

    def __init__(self):
        self.__known_types = {}

    @property
    def known_types(self):
        return self.__known_types.keys()

    def register_type(self, suffixes, node_type) -> None:
        if isinstance(suffixes, str):
            suffixes = [suffixes]

        for suffix in suffixes:
            self.__known_types[suffix] = node_type

    def create_node(self, suffix, src, path, metadata_path=None) -> T:
        class_ = self.__known_types[suffix]
        return class_(src, path, metadata_path)


class ResourceNodeFactory(NodeFactory[ResourceNode]):
    def __init__(self):
        super().__init__()
        self.register_type(['.sass', '.scss'], SassResourceNode)


class DocumentNodeFactory(NodeFactory[DocumentNode]):
    def __init__(self):
        super().__init__()
        self.register_type(['.md'], MarkdownDocumentNode)
        self.register_type(['.html'], HtmlDocumentNode)


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

    @property
    def is_image(self):
        return self.src.suffix in {'.jpg', '.png'}

    def publish(self, publisher: Publisher) -> pathlib.Path:
        return publisher.publish_static(self)


class ThumbnailNode(ResourceNode):
    def __init__(self, src, path, size):
        super().__init__(src, path)
        self.__size = size

    def __get_hash_key(self) -> bytes:
        import hashlib
        hash_key = hashlib.sha256(self.src.open('rb').read()).digest()

        if 'height' in self.__size:
            hash_key += self.__size['height'].to_bytes(4, 'little')
        else:
            hash_key += bytes([0, 0, 0, 0])

        if 'width' in self.__size:
            hash_key += self.__size['width'].to_bytes(4, 'little')
        else:
            hash_key += bytes([0, 0, 0, 0])

        return hash_key

    def process(self, cache: Cache):
        from PIL import Image
        import io

        hash_key = self.__get_hash_key()
        if cache.contains(hash_key):
            self.content = cache.get(hash_key)
            return

        image = Image.open(self.src)
        width, height = image.size

        scale = 1
        if 'height' in self.__size:
            scale = min(self.__size['height'] / height, scale)
        if 'width' in self.__size:
            scale = min(self.__size['width'] / width, scale)
        width *= scale
        height *= scale

        image.thumbnail((width, height,))
        storage = io.BytesIO()
        if self.src.suffix == '.jpg':
            image.save(storage, 'JPEG')
            self.content = storage.getbuffer()
        elif self.src.suffix == '.png':
            image.save(storage, 'PNG')
            self.content = storage.getbuffer()
        else:
            raise Exception("Unsupported image type for thumbnails")

        cache.put(hash_key, bytes(self.content))
