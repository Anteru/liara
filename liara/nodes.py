from enum import auto, Enum
import pathlib
from .yaml import load_yaml
import toml
from .cache import Cache
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)
import re
import dateparser


T = TypeVar('T')


class Publisher:
    """A publisher produces the final output files, applying templates etc. as
    needed.
    """
    def publish_document(self, document: 'DocumentNode'):
        """Publish a document node."""
        pass

    def publish_index(self, index: 'IndexNode'):
        """Publish an index node."""
        pass

    def publish_resource(self, resource: 'ResourceNode'):
        """Publish a resource node."""
        pass

    def publish_static(self, static: 'StaticNode'):
        """Publish a static node."""
        pass

    def publish_generated(self, generated: 'GeneratedNode'):
        """Publish a generated node."""
        pass


class NodeKind(Enum):
    Resource = auto()
    Index = auto()
    Document = auto()
    Data = auto()
    Static = auto()
    Generated = auto()


class Node:
    kind: NodeKind
    """The node kind, must be set in the constructor."""
    src: pathlib.Path
    """The full path to the source file.

    This is an OS specific path object."""

    path: pathlib.PurePosixPath
    """The output path, relative to the page root.

    All paths *must* start with ``/``.
    """

    metadata: Dict[str, Any]
    """Metadata associated with this node."""

    parent: Optional['Node']
    """The parent node, if any."""

    __nodes: Dict[str, 'Node']
    """A dictionary containing all child nodes.

    The key is the path to the child node relative to this node. I.e. if the
    path of this node is ``/foo``, and it has a child at ``/foo/bar``, the
    key for that child would be ``bar``."""

    @property
    def children(self):
        """A list containing all direct children of this node."""
        return self.__nodes.values()

    def __init__(self):
        self.__nodes = {}
        self.metadata = {}
        self.parent = None

    def add_child(self, child: 'Node') -> None:
        """Add a new child to this node.

        The path of the child node must be a sub-path of the current node
        path, with exactly one more component. I.e. if the current node path is
        ``/foo/bar``, a node with path ``/foo/bar/baz`` can be added as a
        child, but ``/baz/`` or ``/foo/bar/boo/baz`` would be invalid."""
        assert self.path != child.path
        name = child.path.relative_to(self.path).parts[0]
        self.__nodes[name] = child
        child.parent = self

    def __repr__(self):
        return f'{self.__class__.__name__}({self.path})'

    def select_children(self):
        """Select all children of this node and return them as a 
        :py:class:`~liara.query.Query`."""
        from .query import Query
        return Query(self.children)

    def get_child(self, name) -> Optional['Node']:
        """Get a child of this node.

        :return: The child node or ``None`` if no such child exists."""
        return self.__nodes.get(name)

    def get_children(self, *, recursive=False) -> Iterable['Node']:
        """Get all children of this node.

        This function differs from :py:meth:`select_children` in two important
        ways:

        * It returns a list of :py:class:`Node` instances and does not wrap it
          in a :py:class:`~liara.query.Query`
        * It can enumerate all children recursively.
        """
        for child in self.children:
            yield child
            if recursive:
                yield from child.get_children(recursive=True)

    def process(self, cache: Cache) -> None:
        """Some nodes -- resources, documents, etc. need to be processed. As
        this can be a resource-intense process (for instance, it may require
        generating images), processing can cache results and has to be
        called separately instead of being executed as part of some other
        operation.

        By convention this method should populate ``self.content``.
        """
        pass


_metadata_marker = re.compile(r'(---|\+\+\+)\n')


class MetadataKind(Enum):
    Unknown = auto()
    Yaml = auto()
    Toml = auto()


def extract_metadata_content(text: str):
    """Extract metadata and content.

    Metadata is stored at the beginning of the file, separated using a metadata
    seperation marker, for instance::

      +++
      this_is_toml = True
      +++

      content

    This function splits the provided text into metadata and actual content.
    """
    meta_start, meta_end = 0, 0
    content_start, content_end = 0, 0
    metadata_kind = MetadataKind.Unknown

    # If the document doesn't end with a trailing new-line, the metadata regex
    # will get confused. We'll thus add a new-line to make sure this works
    if text[-1] != '\n':
        text += '\n'

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
        metadata = toml.loads(text[meta_start:meta_end])
    else:
        # We didn't find any metadata here, so everything must be content
        return None, text

    content = text[content_start:content_end]
    return metadata, content


def fixup_relative_links(document: 'DocumentNode'):
    """Replace relative links in the document with links relative to the
    site root."""
    # early out if there's no relative link in here, as the parsing is
    # very expensive
    if "href=\"." not in document.content:
        return

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(document.content, 'lxml')

    def is_relative_url(s):
        return s and s[0] == '.'

    for link in soup.find_all('a', {'href': is_relative_url}):
        target = link.attrs.get('href')
        link.attrs['href'] = \
            str(document.path.parent / pathlib.PurePosixPath(target))

    document.content = str(soup)


def fixup_date(document: 'DocumentNode'):
    """If the date in the document is a string, try to parse it to produce a
    datetime object."""
    if 'date' in document.metadata:
        date = document.metadata['date']
        if isinstance(date, str):
            document.metadata['date'] = dateparser.parse(date)


class FixupDateTimezone:
    """Set the timezone of the ``metadata['date']`` field to the local timezone
    if no timezone has been set."""
    def __init__(self):
        import tzlocal
        self.__tz = tzlocal.get_localzone()

    def __call__(self, document: 'DocumentNode'):
        '''If the date in the document has no timezone info, set it to the local
        timezone.'''
        if 'date' in document.metadata:
            date = document.metadata['date']
            if date.tzinfo is None:
                document.metadata['date'] = self.__tz.localize(date)


class DocumentNode(Node):
    _load_fixups: List[Callable]
    """These functions are called right after the document has been loaded,
    and can be used to fixup metadata, content, etc. before it gets processed
    (These should be called before :py:meth:`load`/:py:meth:`reload`
    returns.)"""

    _process_fixups: List[Callable]
    """These functions are called after a document has been processed
    (These should be called before :py:meth:`process` returns)."""

    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Document
        self.src = src
        self.path = path
        self.metadata_path = metadata_path
        self.content = None
        self._load_fixups = []
        self._process_fixups = []

    def set_fixups(self, *, load_fixups, process_fixups) -> None:
        """Set the fixups that should be applied to this document node.
        The fixups should be set *before* calling :py:meth:`load`.

        :param load_fixups: These functions will be executed before
                            :py:meth:`load` returns.
        :param process_fixups: These functions will be executed before
                            :py:meth:`process` returns.
        """
        self._load_fixups = load_fixups
        self._process_fixups = process_fixups

    def load(self):
        """Load the content of this node."""
        self._load()
        self._apply_load_fixups()

    def validate_metadata(self):
        if self.metadata is None:
            raise Exception(f"No metadata for document: '{self.src}'")
        if 'title' not in self.metadata:
            raise Exception(f"'title' missing for Document: '{self.src}'")

    def _apply_load_fixups(self):
        for fixup in self._load_fixups:
            fixup(self)

    def _apply_process_fixups(self):
        for fixup in self._process_fixups:
            fixup(self)

    def _load(self):
        if self.metadata_path:
            self.metadata = load_yaml(self.metadata_path.read_text())
            self._raw_content = self.src.read_text('utf-8')
        else:
            self.metadata, self._raw_content = \
                extract_metadata_content(self.src.read_text('utf-8'))

    def reload(self):
        """Reload this node from disk.

        By default, this just forwards to :py:meth:`_load`.
        """
        self._load()
        self._apply_load_fixups()

    def publish(self, publisher: Publisher) -> pathlib.Path:
        """Publish this node using the provided publisher."""
        return publisher.publish_document(self)


class HtmlDocumentNode(DocumentNode):
    """A node representing a Html document."""

    def process(self, cache: Cache):
        self.content = self._raw_content

        self._apply_process_fixups()

        return self


class MarkdownDocumentNode(DocumentNode):
    """A node representing a Markdown document."""
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
        self._apply_process_fixups()

        cache.put(content_hash, self.content)
        return self


class DataNode(Node):
    """A data node.

    Data nodes consist of a dictionary. This can be used to store arbitrary
    data as part of a :py:class:`liara.site.Site`, and make it available to
    templates (for instance, a menu structure could go into a data node.)
    """
    def __init__(self, src, path):
        super().__init__()
        self.kind = NodeKind.Data
        self.src = src
        self.path = path
        self.content = load_yaml(self.src.open('r'))


class IndexNode(Node):
    """An index node.

    Index nodes are created for every folder if there is no ``_index`` node
    present, and from indices. An index node can optionally contain a list of
    references, in case the referenced nodes by this index are not direct
    children of this node.
    """

    references: List[Node]
    """Referenced nodes by this index.

    An index can not rely on using ``children`` as those have to be below the
    path of the parent node. The ``references`` list allows to reference nodes
    elsewhere in the site."""

    def __init__(self, path, metadata={}):
        super().__init__()
        self.kind = NodeKind.Index
        self.src = None
        self.path = path
        self.metadata = metadata
        self.references = []

    def add_reference(self, node):
        """Add a reference to an arbitrary node in the site."""
        self.references.append(node)

    def publish(self, publisher) -> pathlib.Path:
        """Publish this node using the provided publisher."""
        return publisher.publish_index(self)


class GeneratedNode(Node):
    def __init__(self, path, metadata={}):
        super().__init__()
        self.kind = NodeKind.Generated
        self.src = None
        self.path = path
        self.metadata = metadata

    def generate(self) -> None:
        """Generate the content of this node.

        After this function has finished, ``self.content`` must be populated
        with the generated content."""
        pass

    def publish(self, publisher: Publisher):
        """Publish this node using the provided publisher."""
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
    """A redirection node triggers a redirection to another page.

    This node gets processed into a simple web site which tries to redirect
    using both ``<meta http-equiv="refresh">`` and Javascript code setting
    ``window.location``.
    """

    def __init__(self,
                 path: pathlib.PurePosixPath,
                 dst: pathlib.PurePosixPath):
        super().__init__(path)
        self.dst = dst

    def generate(self):
        text = _REDIRECTION_TEMPLATE.replace('{{NEW_URL}}',
                                             self.dst.as_posix())
        self.content = text


class ResourceNode(Node):
    """A resource node applies some process when creating the output.

    This is useful if you have content where the source cannot be interpreted,
    and requires some process first before it becomes usable -- for instance,
    ``SASS`` to ``CSS`` compilation.
    """
    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Resource
        self.src = src
        self.path = path
        self.content = None
        if metadata_path:
            self.metadata = load_yaml(open(metadata_path, 'r'))

    def reload(self) -> None:
        pass

    def publish(self, publisher: Publisher) -> pathlib.Path:
        """Publish this node using the provided publisher."""
        return publisher.publish_resource(self)


class SassResourceNode(ResourceNode):
    """This resource node compiles ``.sass`` and ``.scss`` files to CSS
    when built.
    """

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
    """A generic factory for nodes, which builds nodes based on the file
    type."""
    __known_types: Dict[str, Type]

    def __init__(self):
        self.__known_types = {}

    @property
    def known_types(self):
        return self.__known_types.keys()

    def register_type(self,
                      suffixes: Union[str, Iterable[str]],
                      node_type: type) -> None:
        """Register a new node type.

        :param suffixes: Either one suffix, or a list of suffixes to be
                         registered for this type. For instance, a node
                         representing an image could be registered to
                         ``[.jpg, .png]``.
        :param node_type: The type of the node to be created.
        """
        if isinstance(suffixes, str):
            suffixes = [suffixes]

        for suffix in suffixes:
            self.__known_types[suffix] = node_type

    def _create_node(self, cls, src, path, metadata_path) -> T:
        """This is the actual creation function.

        :param cls: The class of the node to instantiate.
        :param src: The source file path.
        :param path: The output path.
        :param metadata_path: The path to a metadata file.
        :return: An instance of ``cls``.

        Derived classes can use this function to customize the node creation.
        """
        return cls(src, path, metadata_path)

    def create_node(self, suffix: str,
                    src: pathlib.Path,
                    path: pathlib.PurePosixPath,
                    metadata_path: Optional[pathlib.Path]=None) -> T:
        """Create a node using the provided parameters."""
        cls = self.__known_types[suffix]
        return self._create_node(cls, src, path, metadata_path)


class ResourceNodeFactory(NodeFactory[ResourceNode]):
    """A factory for resource nodes."""
    def __init__(self):
        super().__init__()
        self.register_type(['.sass', '.scss'], SassResourceNode)


class DocumentNodeFactory(NodeFactory[DocumentNode]):
    """A factory for document nodes."""
    def __setup_fixups(self, configuration):
        if configuration['relaxed_date_parsing']:
            # This is tricky, as fixup_date_timezone depends on this running
            # first. We thus prepend this before any other fixup and hope this
            # is the only one with ordering issues.
            self.__load_fixups.insert(0, fixup_date)
        if configuration['allow_relative_links']:
            self.__process_fixups.append(fixup_relative_links)

    def __init__(self, configuration):
        super().__init__()
        self.__load_fixups = [FixupDateTimezone()]
        self.__process_fixups = []

        self.__setup_fixups(configuration)

        self.register_type(['.md'], MarkdownDocumentNode)
        self.register_type(['.html'], HtmlDocumentNode)

    def _create_node(self, cls, src, path, metadata_path=None):
        node = cls(src, path, metadata_path)
        node.set_fixups(
            load_fixups=self.__load_fixups,
            process_fixups=self.__process_fixups)
        node.load()
        return node


class StaticNode(Node):
    """A static data node.

    Static nodes are suitable for large static data which never changes, for
    instance, binary files, videos, images etc.
    """
    def __init__(self, src, path, metadata_path=None):
        super().__init__()
        self.kind = NodeKind.Static
        self.src = src
        self.path = path
        if metadata_path:
            self.metadata = load_yaml(open(metadata_path, 'r'))

    def update_metadata(self) -> None:
        """Update metadata by deriving some metadata from the source file,
        if possible.

        For static nodes pointing to images, this will create a new metadata
        field ``image_size`` and populate it with the image resolution."""
        from PIL import Image
        if self.is_image:
            image = Image.open(self.src)
            self.metadata.update({
                'image_size': image.size
            })

    @property
    def is_image(self):
        """Return ``True`` if this static file is pointing to an image."""
        return self.src.suffix in {'.jpg', '.png'}

    def publish(self, publisher: Publisher) -> pathlib.Path:
        """Publish this node using the provided publisher."""
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
