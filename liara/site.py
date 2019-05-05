from .nodes import (
    DataNode,
    IndexNode,
    DocumentNode,
    ResourceNode,
    Node,
    StaticNode,
    GeneratedNode,
    ThumbnailNode,
)
import pathlib
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
)
from .util import pairwise
import datetime
import logging


def _create_metadata_accessor(field_name):
    """Create an accessor for nested metadata fields.

    This allows accessing attributes or dictionary entries recursively, i.e.
    an accessor ``foo.bar.baz`` will access ``foo['bar']['baz]`` and
    ``foo.bar.baz``, and any combination thereof. Attributes will be preferred
    over dictionary access.
    """
    import operator
    if '.' in field_name:
        def key_fun(o):
            field = field_name.split('.')
            o = o.metadata[field[0]]
            for f in field[1:]:
                if hasattr(o, f):
                    o = getattr(o, f)
                else:
                    o = o[f]
            return o
        return key_fun
    else:
        def key_fun(o):
            return o.metadata[field_name]
        return key_fun


class Collection:
    """A collection is a set of nodes. Collections can be ordered, which allows
    for next/previous queries.
    """

    __log = logging.getLogger('liara.Collection')

    def __init__(self, site, pattern, order_by=[]):
        """
        :param pattern: The pattern to select nodes which belong to this
                        collection.
        :param order_by: A list of accessors for fields to order by. If
                         multiple entries are provided, the result will be
                         sorted by each in order using a stable sort.

        If an ordering is specified, and a particular node cannot support that
        ordering (for instance, as it's missing the field that is used to order
        by), the node will be *removed* from the collection.
        """
        self.__site = site
        self.__filter = pattern
        # We accept a string as well to simplify configuration files
        if isinstance(order_by, str):
            self.__order_by = [order_by]
        else:
            self.__order_by = order_by
        self.__build()

    def __build(self):
        nodes = self.__site.select(self.__filter)

        # We want to remove all nodes that don't have the required fields,
        # as it doesn't make much sense to ask for ordering if some nodes
        # cannot be ordered
        def filter_fun(o):
            for ordering in self.__order_by:
                # we need to match the metadata accessor logic below
                if '.' in ordering:
                    ordering = ordering.split('.')[0]
                if ordering not in o.metadata:
                    return False
            return True

        nodes = filter(filter_fun, nodes)

        for ordering in self.__order_by:
            key_fun = _create_metadata_accessor(ordering)
            nodes = sorted(nodes, key=key_fun)
        pairs = list(pairwise(nodes))
        self.__next = {i[0].path: i[1] for i in pairs}
        self.__previous = {i[1].path: i[0] for i in pairs}
        self.__nodes = {n.path: n for n in nodes}

    @property
    def nodes(self):
        """Get the (sorted) nodes in this collection."""
        return self.__nodes.values()

    def get_next(self, node):
        """Get the next node in this collection with regard to the specified
        order, or ``None`` if this is the last node."""
        if not self.__order_by:
            self.__log.warn('Using get_next() on an unordered collection has '
                            'undefined results')
        return self.__next.get(node.path)

    def get_previous(self, node):
        """Get the previous node in this collection with regard to the specified
        order, or ``None`` if this is the first node."""
        if not self.__order_by:
            self.__log.warn('Using get_next() on an unordered collection has '
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
            result = {k: _group_recursive(v, group_keys)
                      for k, v in result.items()}
        return result
    else:
        key_func = _create_metadata_accessor(current_key)
        iterable = sorted(iterable, key=key_func)
        result = {}
        for k, v in itertools.groupby(iterable, key_func):
            values = _group_recursive(v, group_keys)
            result[k] = values
        return result


class Index:
    """An index provides an index for a collection, by generating index nodes
    for the collection.
    """
    def __init__(self, site, collection: Collection,
                 path: str, group_by=[], *,
                 create_top_level_index=False):
        nodes = collection.nodes
        self.__groups = _group_recursive(nodes, group_by)
        self.__site = site
        self.__path = path
        self.__create_top_level_index = create_top_level_index

    def create_nodes(self, site):
        """Create the index nodes inside the specified site."""
        self._create_nodes_recursive(site, self.__path,
                                     self.__groups, 1)

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

    def _create_nodes_recursive(self, site, path, d, index):
        for k, v in d.items():
            url = pathlib.PurePosixPath(path.replace(f'%{index}', str(k)))
            # TODO Find out what to do here -- either don't create intermediate
            # nodes (i.e. as long as one %N placeholder is left), or cut off
            # the URL.
            node = IndexNode(url, {'key': k})
            site.add_index(node)
            if isinstance(v, dict):
                self._create_nodes_recursive(site, url, v, index+1)
            else:
                for reference in v:
                    node.add_reference(reference)


class ContentFilter:
    """Content filters can filter out nodes based on various criteria."""
    def apply(self, node: Node) -> bool:
        """Return ``True`` if the node should be kept, and ``False``
        otherwise.
        """
        pass


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

        if date.tzinfo is None:
            date = self.__tz.localize(date)
        return date <= self.__now

    @property
    def reason(self):
        return 'date <= now()'


class StatusFilter(ContentFilter):
    """Filter content based on the metadata field ``status``.

    If ``status`` is set to ``private``, the node will be filtered. The
    comparison is case-insensitive.
    """
    def apply(self, node: Node) -> bool:
        return node.metadata.get('status', '').lower() != 'private'

    @property
    def reason(self):
        return 'status set to "private"'


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
        self.__log = logging.getLogger('liara.site')

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
                self.__log.info(f'Filtered node {node.path} due to {f.reason}')
                return True
        return False

    def add_data(self, node: DataNode) -> None:
        "Add a data node to this site."""
        self.data.append(node)
        self.__register_node(node)

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
            raise Exception(f'"{node.path}" already exists, cannot overwrite.')
        self.__nodes[node.path] = node

    @property
    def nodes(self) -> Iterable[Node]:
        """The list of all nodes in this site."""
        return self.__nodes.values()

    @property
    def urls(self) -> Iterable[pathlib.PurePosixPath]:
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
            self.__collections[name] = Collection(self, collection['filter'],
                                                  order_by)

    def create_indices(self, indices):
        """Create indices."""
        for index_definition in indices:
            collection = self.get_collection(index_definition['collection'])
            del index_definition['collection']
            index = Index(self, collection, **index_definition)
            self.__indices.append(index)

        for index in self.__indices:
            index.create_nodes(self)

        # Indices may have been added, so we need to update the links
        self.create_links()

    def create_thumbnails(self, thumbnail_definition):
        """Create thumbnails.

        Based on the thumbnail definition -- which is assumed to be a
        dictionary containing the suffix and the desired size -- this function
        iterates over all static nodes that contain images, and creates new
        thumbnail nodes as required.
        """
        from .util import add_suffix
        new_static = []
        for static in self.static:
            if not static.is_image:
                continue
            static.update_metadata()
            width, height = static.metadata['image_size']
            for k, v in thumbnail_definition.items():
                new_url = add_suffix(static.path, k)
                thumbnail_width = v.get('width', width)
                thumbnail_height = v.get('height', height)
                if width <= thumbnail_width and height <= thumbnail_height:
                    # The image has the right size already (smaller or equal
                    # to the thumbnail), so we just link a new static node
                    copy = StaticNode(static.src, new_url)
                    copy.metadata = static.metadata
                    new_static.append(copy)
                else:
                    thumbnail = ThumbnailNode(static.src, new_url, v)
                    self.add_resource(thumbnail)

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

    def get_node(self, path: pathlib.PurePosixPath) -> Optional[Node]:
        """Get a node based on the URL, or ``None`` if no such node exists."""
        return self.__nodes.get(path)

    def select(self, query: str) -> Iterable[Node]:
        """Select nodes from this site.
        
        The query string may contain ``*`` to list all direct children of a
        node, and ``**`` to recursively enumerate nodes. Partial matches
        using ``*foo`` are not supported."""
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

            node = node.get_child(component)
            if node is None:
                return []
        return node
