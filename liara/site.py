from .nodes import (
    DataNode,
    DocumentNode,
    GeneratedNode,
    IndexNode,
    Node,
    NodeKind,
    ResourceNode,
    StaticNode,
    ThumbnailNode,
)
import pathlib
from typing import (
    Any,
    Dict,
    Iterable,
    KeysView,
    List,
    Optional,
    Tuple,
    Union,
    ValuesView,
)
from .util import pairwise, merge_dictionaries
from . import signals
import logging
import fnmatch
from abc import abstractmethod, ABC
from types import MappingProxyType


def _create_metadata_accessor(field_name: str):
    """Create an accessor for nested metadata fields.

    This allows accessing attributes or dictionary entries recursively, i.e.
    an accessor ``foo.bar.baz`` will access ``foo['bar']['baz]`` and
    ``foo.bar.baz``, and any combination thereof. Attributes will be preferred
    over dictionary access.

    If the field is not present, this function returns ``None``.
    """
    if '.' in field_name:
        def dict_key_fun(o):
            field = field_name.split('.')
            o = o.metadata.get(field[0])
            if o is None:
                return None
            for f in field[1:]:
                if hasattr(o, f):
                    o = getattr(o, f)
                elif f in o:
                    o = o[f]
                else:
                    return None
            return o
        return dict_key_fun
    else:
        def metadata_key_fun(o):
            return o.metadata.get(field_name)
        return metadata_key_fun


def _create_metadata_filter(exclude_without:
                            List[Union[str, Tuple[str, Any]]]):
    """Create a function to filter out nodes based on metadata fields.

    The filter function will check if the specified fields are present,
    and, if a tuple has been passed, if that field matches the expected
    value."""
    key_functions = []
    for f in exclude_without:
        if isinstance(f, str):
            key = f

            def key_function(node: Node):
                return _create_metadata_accessor(key)(node) is not None
            key_functions.append(key_function)
        else:
            assert isinstance(f, tuple)
            assert len(f) == 2
            key = f[0]

            def key_function(node: Node):
                return _create_metadata_accessor(key)(node) == f[1]
            key_functions.append(key_function)

    def filter_function(node: Node):
        for key_function in key_functions:
            if not key_function(node):
                return False
        return True

    return filter_function


class Collection:
    """A collection is a set of nodes. Collections can be ordered, which allows
    for next/previous queries.
    """

    __log = logging.getLogger(f'{__name__}.{__qualname__}')

    def __init__(self, site: 'Site', name: str, pattern: str, *,
                 exclude_without: Optional[List[Union[str, Tuple[str, Any]]]]
                 = None,
                 order_by: Optional[Union[str, List[str]]] = None,
                 node_kinds: Optional[List[Union[str, NodeKind]]] = None):
        """
        Create a new collection.

        :param pattern: The pattern to select nodes which belong to this
                        collection.
        :param exclude_without: Exclude items without the specified metadata
                          fields. If a tuple is provided, the metadata field's
                          value must match the requested value.
        :param order_by: A list of accessors for fields to order by. If
                         multiple entries are provided, the result will be
                         sorted by each in order using a stable sort. To
                         reverse the order, use a leading ``-``, for
                         example: ``-date``.
        :param node_kinds: Only include nodes of that kinds. If not specified,
                           ``NodeKind.Document`` will be used as the default.

        If an ordering is specified, and a particular node cannot support that
        ordering (for instance, as it's missing the field that is used to order
        by), an error will be raised.
        """
        from .nodes import _parse_node_kind

        self.__name = name

        self.__site = site
        self.__filter = pattern
        self.__node_kinds = set()
        if node_kinds:
            for kind in node_kinds:
                if isinstance(kind, NodeKind):
                    self.__node_kinds.add(kind)
                else:
                    self.__node_kinds.add(_parse_node_kind(kind))
        else:
            self.__node_kinds.add(NodeKind.Document)

        self.__order_by = order_by if order_by else []

        self.__exclude_without = exclude_without
        self.__build()

    def __build(self):
        nodes = self.__site.select(self.__filter)

        def filter_kind(node):
            return node.kind in self.__node_kinds

        nodes = filter(filter_kind, nodes)

        if self.__exclude_without:
            nodes = filter(_create_metadata_filter(self.__exclude_without),
                           nodes)

        for ordering in self.__order_by:
            if ordering.startswith('-'):
                ordering = ordering[1:]
                reverse = True
            else:
                reverse = False

            def key_fun(node):
                accessor = _create_metadata_accessor(ordering)
                result = accessor(node)
                if result is None:
                    self.__log.error(
                        'Node "%s" is missing the metadata '
                        'field "%s" which is required by a '
                        'order_by statement. Use exclude_without to '
                        'excludes nodes which miss certain metadata '
                        'fields.',
                        node.path, ordering)
                    raise Exception(f'Cannot order collection "{self.__name}" '
                                    f'by key "{ordering}"')
                return result

            nodes = sorted(nodes, key=key_fun, reverse=reverse)

        # Need to convert to a list here, as we're going to iterate over it
        # twice (once for the pairs, once for the nodes property)
        nodes = list(nodes)

        pairs = list(pairwise(nodes))
        self.__next = {i[0].path: i[1] for i in pairs}
        self.__previous = {i[1].path: i[0] for i in pairs}
        self.__nodes = {n.path: n for n in nodes}

    @property
    def nodes(self) -> Iterable[Node]:
        """Get the (sorted) nodes in this collection."""
        return self.__nodes.values()

    def get_next(self, node: Node) -> Optional[Node]:
        """Get the next node in this collection with regard to the specified
        order, or ``None`` if this is the last node."""
        if not self.__order_by:
            self.__log.warning(
                'Using get_next() on an unordered collection has '
                'undefined results')
        return self.__next.get(node.path)

    def get_previous(self, node: Node) -> Optional[Node]:
        """Get the previous node in this collection with regard to the
        specified order, or ``None`` if this is the first node."""
        if not self.__order_by:
            self.__log.warning(
                'Using get_next() on an unordered collection has '
                'undefined results')
        return self.__previous.get(node.path)


def _group_recursive(iterable, group_keys: List[str]):
    import collections
    import itertools
    if not group_keys:
        return list(iterable)

    current_key = group_keys[0]
    group_keys = group_keys[1:]
    if current_key[0] == '*':
        key_func = _create_metadata_accessor(current_key[1:])
        # If the group key starts with a *, this means it's a list of items,
        # not a single item to group by -- for instance, a list of tags
        # In this case, we create one bucket per item, append the items to that
        # list, and eventually we recurse if needed
        result = collections.defaultdict(list)
        for item in iterable:
            groups = key_func(item)
            for group in groups:
                result[group].append(item)

        if group_keys:
            return {k: _group_recursive(v, group_keys)
                    for k, v in result.items()}
        return result
    else:
        key_func = _create_metadata_accessor(current_key)
        iterable = sorted(iterable, key=key_func)
        result = dict()
        for k, v in itertools.groupby(iterable, key_func):
            values = _group_recursive(v, group_keys)
            result[k] = values
        return result


class Index:
    __log = logging.getLogger(f'{__name__}.{__qualname__}')

    """An index into a collection, which provides an index structure.

    The index structure requires a grouping schema -- for instance, all nodes
    containing some tag can get grouped under one index node.
    """
    def __init__(self, collection: Collection,
                 path: str, group_by: List[str], *,
                 exclude_without: Optional[List[Union[str, Tuple[str, Any]]]]
                 = None,
                 create_top_level_index=False):
        """
        Create a new index.

        :param collection: The collection to use for this index.
        :param path: The path pattern to create index entries at. This must
                     contain one numbered placeholder (``%1``, etc.) per entry
                     in ``group_by``
        :param group_by: The grouping statements. The nodes are grouped by each
                         entry in this array in-order.
        :param exclude_without: Exclude items without the specified metadata
                          field. If a tuple is provided, the metadata field's
                          value must match the requested value.
        :param create_top_level_index: Create a node at the top-level path as
                                       well instead of only creating nodes
                                       per grouping statement.
        """
        nodes = collection.nodes

        if exclude_without:
            filter_function = _create_metadata_filter(exclude_without)
            nodes = filter(filter_function, nodes)

        assert len(group_by) > 0
        self.__groups = _group_recursive(nodes, group_by)
        self.__path = path
        self.__create_top_level_index = create_top_level_index
        self.__top_level_node: IndexNode | None = None

    def create_nodes(self, site: 'Site'):
        """Create the index nodes inside the specified site."""
        if self.__create_top_level_index:
            url = self.__path
            # Strip off components until we have no parameter left
            while '%' in url:
                url = url[:url.rfind('/')]
            node = IndexNode(pathlib.PurePosixPath(url), {
                'path': self.__path,
                'top_level_index': True
            })
            site.add_index(node)
            self.__top_level_node = node
            self.__log.debug('Created top-level index at "%s"',
                             self.__path)

        self._create_nodes_recursive(site, self.__path,
                                     self.__groups, 1,
                                     self.__top_level_node)

    def _create_nodes_recursive(self, site: 'Site', path, d, index,
                                parent: Optional[IndexNode] = None):
        for k, v in d.items():
            url = pathlib.PurePosixPath(path.replace(f'%{index}', str(k)))
            # TODO Find out what to do here -- either don't create intermediate
            # nodes (i.e. as long as one %N placeholder is left), or cut off
            # the URL.
            node = IndexNode(url, {'key': k})
            site.add_index(node)

            if parent:
                parent.add_reference(node)

            if isinstance(v, dict):
                self._create_nodes_recursive(site, url, v, index+1, node)
            else:
                for reference in v:
                    node.add_reference(reference)


class ContentFilter(ABC):
    """Content filters can filter out nodes based on various criteria."""
    @abstractmethod
    def apply(self, node: Node) -> bool:
        """Return ``True`` if the node should be kept, and ``False``
        otherwise.
        """
        ...

    @property
    def reason(self) -> str:
        """Return a reason why this filter applied."""
        return ''

    @property
    def name(self) -> str:
        return self.__class__.__name__


class DateFilter(ContentFilter):
    """Filter content based on the metadata field ``date``.

    If the date is in the future, the node will be filtered."""
    def __init__(self):
        from .util import local_now
        self.__now = local_now()

    def apply(self, node: Node) -> bool:
        date = node.metadata.get('date', None)
        if date is None:
            return True

        return date <= self.__now

    @property
    def reason(self):
        return f'`date` <= {self.__now}'

    @property
    def name(self):
        return 'date'


class StatusFilter(ContentFilter):
    """Filter content based on the metadata field ``status``.

    If ``status`` is set to ``private``, the node will be filtered. The
    comparison is case-insensitive.
    """
    def apply(self, node: Node) -> bool:
        return node.metadata.get('status', '').lower() != 'private'

    @property
    def reason(self):
        return '`status` set to "private"'

    @property
    def name(self):
        return 'status'


class ContentFilterFactory:
    def __init__(self):
        self.__filters = {
            'date': DateFilter,
            'status': StatusFilter
        }

    def create_filter(self, name: str) -> ContentFilter:
        class_ = self.__filters[name]
        return class_()


class Site:
    """This class manages to all site content."""

    data: List[DataNode]
    """The list of all data nodes in this site."""

    indices: List[IndexNode]
    """The list of all index nodes in this site."""

    documents: List[DocumentNode]
    """The list of all document nodes in this site."""

    resources: List[ResourceNode]
    """The list of all resources nodes in this site."""

    static: List[StaticNode]
    """The list of all static nodes in this site."""

    generated: List[GeneratedNode]
    """The list of all generated nodes in this site."""

    metadata: Dict[str, Any]
    """Metadata describing this site."""

    __nodes: Dict[pathlib.PurePosixPath, Node]
    __root = pathlib.PurePosixPath('/')
    __collections: Dict[str, Collection]
    __indices: List[Index]
    __content_filters: List[ContentFilter]
    __filtered_content: Dict[pathlib.PurePosixPath, str]

    __log = logging.getLogger(f'{__name__}.{__qualname__}')

    __merged_data: Dict[str, Any]

    def __init__(self):
        self.data = []
        self.indices = []
        self.documents = []
        self.resources = []
        self.static = []
        self.generated = []
        self.metadata = {}
        self.__nodes = {}
        self.__collections = {}
        self.__indices = []
        self.__content_filters = []

        # Stores the paths of filtered nodes, and the filter that filtered them
        self.__filtered_content = {}

        # Store the union of the data provided in data nodes
        self.__merged_data = {}

    def register_content_filter(self, content_filter: ContentFilter):
        """Register a new content filter."""
        self.__content_filters.append(content_filter)

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set the metadata for this site.

        This overrides any previously set metadata. Metadata is accessible
        via the :py:attr:`metadata` attribute.
        """
        self.metadata = metadata

    def set_metadata_item(self, key: str, value: Any) -> None:
        """Set a single entry in the metadata for this site.

        This can be used to override individual metadata items.
        """
        self.metadata[key] = value

    def __is_content_filtered(self, node: Node) -> bool:
        for f in self.__content_filters:
            if not f.apply(node):
                self.__log.info('Filtered node "%s" due to reason: %s',
                                node.path, f.reason)
                self.__filtered_content[node.path] = f.name
                signals.content_filtered.send(self, node=node, filter=f)
                return True
        return False

    @property
    def filtered_content(self) -> Dict[pathlib.PurePosixPath, str]:
        """Return which node paths got filtered and due to which filter."""
        return self.__filtered_content

    def add_data(self, node: DataNode) -> None:
        "Add a data node to this site."""
        self.data.append(node)
        self.__register_node(node)

        self.__merged_data = merge_dictionaries(self.__merged_data,
                                                node.content)

    def add_index(self, node: IndexNode) -> None:
        """Add an index node to this site."""
        self.indices.append(node)
        self.__register_node(node)

    def add_document(self, node: DocumentNode) -> None:
        """Add a document to this site."""
        if self.__is_content_filtered(node):
            return

        self.documents.append(node)
        self.__register_node(node)

    def add_resource(self, node: ResourceNode) -> None:
        """Add a resource to this site."""
        if self.__is_content_filtered(node):
            return

        self.resources.append(node)
        self.__register_node(node)

    def add_static(self, node: StaticNode) -> None:
        """Add a static node to this site."""
        if self.__is_content_filtered(node):
            return

        self.static.append(node)
        self.__register_node(node)

    def add_generated(self, node: GeneratedNode) -> None:
        "Add a generated node to this site."""
        self.generated.append(node)
        self.__register_node(node)

    def __register_node(self, node: Node) -> None:
        if node.path in self.__nodes:
            raise Exception(f'"{node.path}" already exists, '
                            'cannot overwrite.')

        signals.content_added.send(self, node=node)
        self.__nodes[node.path] = node

    @property
    def nodes(self) -> ValuesView[Node]:
        """The list of all nodes in this site."""
        return self.__nodes.values()

    @property
    def urls(self) -> KeysView[pathlib.PurePosixPath]:
        """The list of all registered URLs."""
        return self.__nodes.keys()

    def create_links(self):
        """This creates links between parents/children.

        This is a separate step so it can be executed after merging nodes
        from multiple sources, for instance themes. It is safe to call this
        function multiple times to create new links; nodes which already
        have a parent are automatically skipped."""
        for key, node in self.__nodes.items():
            if node.parent:
                # The parent is already set, so there's nothing to do
                continue

            parent_path = key.parent
            parent_node = self.__nodes.get(parent_path)
            # The parent_node != node check is required so the root node
            # doesn't get added to itself (by virtue of / being a parent of /)
            if parent_node and parent_node != node:
                parent_node.add_child(node)

    def create_collections(self, collections):
        """Create collections."""
        for name, collection in collections.items():
            order_by = collection.get('order_by', [])
            if isinstance(order_by, str):
                order_by = [order_by]

            exclude_without = collection.get('exclude_without', [])
            if isinstance(exclude_without, str):
                exclude_without = [exclude_without]

            node_kinds = collection.get('node_kinds', [])

            self.__log.debug('Creating collection "%s" ... ', name)
            collection = Collection(self, name,
                                    collection['filter'],
                                    order_by=order_by,
                                    exclude_without=exclude_without,
                                    node_kinds=node_kinds)
            self.__collections[name] = collection
            self.__log.debug('... done creating collection "%s" ... ', name)

    def create_indices(self, indices):
        """Create indices."""
        for index_definition in indices:
            collection = self.get_collection(index_definition['collection'])
            del index_definition['collection']
            create_top_level_index = index_definition.get(
                'create_top_level_index', False
            )

            group_by = index_definition.get('group_by')
            if isinstance(group_by, str):
                group_by = [group_by]

            exclude_without = index_definition.get('exclude_without', [])
            if isinstance(exclude_without, str):
                exclude_without = [exclude_without]

            self.__log.debug('Creating index for path "%s" ...',
                             index_definition['path'])
            index = Index(collection, index_definition['path'],
                          group_by=group_by,
                          exclude_without=exclude_without,
                          create_top_level_index=create_top_level_index)
            self.__indices.append(index)
            self.__log.debug('... done creating index for path "%s"',
                             index_definition['path'])

        for index in self.__indices:
            index.create_nodes(self)

        # Indices may have been added, so we need to update the links
        self.create_links()

    def create_thumbnails(self, thumbnail_definition):
        """Create thumbnails.

        Based on the thumbnail definition -- which is assumed to be a
        dictionary containing the suffix, the desired size and the target
        formats  -- this function iterates over all static nodes that contain
        images, and creates new thumbnail nodes as required.
        """
        from .util import add_suffix

        def create_thumbnail(node: StaticNode, new_path, format, size):
            if format == 'original':
                format = None
            else:
                new_path = new_path.with_suffix(
                    f'.{format.lower()}'
                )

            assert node.src

            if self.get_node(new_path):
                # This happens when the thumbnail format is the same as the
                # image format, and both 'original' and the format are
                # specified
                # This isn't really a problem and fixing this at a higher level
                # isn't any easier than doing it here
                self.__log.debug(
                    'Skipping ".%s" thumbnail creation for "%s" as '
                    'that image already exists as "%s"',
                    format if format else node.src.suffix[1:],
                    node.src,
                    new_path)
                return

            thumbnail = ThumbnailNode(
                node.src,
                new_path,
                size,
                format)
            self.add_resource(thumbnail)

        new_static = []
        for static in self.static:
            if not static.is_image:
                continue
            static.update_metadata()
            assert static.src
            width, height = static.metadata['$image_size']
            for k, v in thumbnail_definition['sizes'].items():
                if 'exclude' in v and 'include' in v:
                    self.__log.warning('Thumbnail size "%s" has both '
                                       '"include" and "exclude" filters '
                                       'enabled, "include" will be ignored.')

                if pattern := v.get('exclude'):
                    if fnmatch.fnmatch(static.src.name, pattern):
                        self.__log.debug(
                                'Skipping thumbnail creation for "%s" due to '
                                'exclude filter "%s"',
                                static.src, pattern)
                        continue
                elif pattern := v.get('include'):
                    if not fnmatch.fnmatch(static.src.name, pattern):
                        self.__log.debug(
                                'Skipping thumbnail creation for "%s" due to '
                                'include filter "%s"',
                                static.src, pattern)
                        continue

                new_url = add_suffix(static.path, k)
                if self.get_node(new_url):
                    self.__log.debug('Skipping thumbnail creation for "%s" '
                                     'as a file with the same name already '
                                     'exists ("%s")', static.src, new_url)
                    continue
                thumbnail_width = v.get('width', width)
                thumbnail_height = v.get('height', height)
                if width <= thumbnail_width and height <= thumbnail_height:
                    # Check for any other formats present and generate those
                    # as needed
                    for format in thumbnail_definition['formats']:
                        if format == 'original':
                            # The image has the right size already (smaller or
                            # equal to the thumbnail), so we just link a new
                            # static node
                            self.__log.debug(
                                'Copying image "%s" for thumbnail as size '
                                '%d x %d is larger or equal than image size '
                                '%d x %d',
                                static.src,
                                width, height,
                                thumbnail_width, thumbnail_height)
                            copy = StaticNode(static.src, new_url)
                            copy.metadata = static.metadata
                            new_static.append(copy)
                        else:
                            self.__log.debug(
                                'Converting image "%s" for thumbnail due to '
                                'format change request to ".%s"',
                                static.src, format)
                            create_thumbnail(static, new_url, format, {})
                else:
                    for format in thumbnail_definition['formats']:
                        create_thumbnail(static, new_url, format, v)

        for static in new_static:
            self.add_static(static)

        # Static nodes may have been created, so we need to update the links
        self.create_links()

    def get_next_in_collection(self,
                               collection: str,
                               node: Node) -> Optional[Node]:
        """Get the next node in a collection."""
        next_node = self.__collections[collection].get_next(node)
        return next_node

    def get_previous_in_collection(self,
                                   collection: str,
                                   node: Node) -> Optional[Node]:
        """Get the previous node in a collection."""
        previous_node = self.__collections[collection].get_previous(node)
        return previous_node

    def get_collection(self, collection: str) -> Collection:
        """Get a collection."""
        return self.__collections[collection]

    def get_node(self, path: Union[str, pathlib.PurePosixPath]) \
            -> Optional[Node]:
        """Get a node based on the URL, or ``None`` if no such node exists."""
        if isinstance(path, str):
            path = pathlib.PurePosixPath(path)
        return self.__nodes.get(path)

    def select(self, query: str) -> Iterable[Node]:
        """Select nodes from this site.

        The query string may contain ``*`` to list all direct children of a
        node, and ``**`` to recursively enumerate nodes. Partial matches
        using ``*foo`` are not supported. See :doc:`/content/url-patterns` for
        details.
        """
        parts = query.split('/')
        # A valid query must start with /
        assert parts[0] == ''
        node = self.__nodes[self.__root]
        for component in parts[1:]:
            if component == '**':
                return node.get_children(recursive=True)
            if component == '*':
                return node.get_children(recursive=False)
            if component == '':
                return [node]

            if (next_child := node.get_child(component)) is None:
                return []
            else:
                node = next_child

        return [node]

    @property
    def merged_data(self) -> MappingProxyType[str, Any]:
        """Return the union of all data nodes.

        This is a read-only view, as shortcodes and templates can access the
        data in any order and thus modifications would be unsafe.
        
        .. versionadded:: 2.6.2
        """
        return MappingProxyType(self.__merged_data)