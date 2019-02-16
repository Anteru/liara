from .nodes import (
    DataNode,
    IndexNode,
    DocumentNode,
    ResourceNode,
    Node,
    StaticNode,
    GeneratedNode,
)
import pathlib
from typing import (
    Dict,
    Iterable,
    List,
    Optional,
)
from .util import pairwise


class Collection:
    def __init__(self, site, pattern, order_by=[]):
        self.__site = site
        self.__filter = pattern
        # We accept a string as well to simplify configuration files
        if isinstance(order_by, str):
            self.__order_by = [order_by]
        else:
            self.__order_by = order_by
        self.__build()

    def __build(self):
        import operator
        nodes = self.__site.select(self.__filter)

        # We want to remove all nodes that don't have the required fields,
        # as it doesn't make much sense to ask for ordering if some nodes
        # cannot be ordered
        def filter_fun(o):
            for ordering in self.__order_by:
                if ordering not in o.metadata:
                    return False
            return True

        nodes = filter(filter_fun, nodes)

        for ordering in self.__order_by:
            if '.' in ordering:
                def key_fun(o):
                    accessor = operator.attrgetter(ordering)
                    metadata = o.metadata
                    return accessor(metadata)
                nodes = sorted(nodes, key=key_fun)
            else:
                def key_fun(o):
                    return o.metadata[ordering]
                nodes = sorted(nodes, key=key_fun)
        pairs = list(pairwise(nodes))
        self.__next = {i[0].path: i[1] for i in pairs}
        self.__previous = {i[1].path: i[0] for i in pairs}
        self.__nodes = {n.path: n for n in nodes}

    @property
    def nodes(self):
        return self.__nodes.values()

    def get_next(self, node):
        return self.__next.get(node.path)

    def get_previous(self, node):
        return self.__previous.get(node.path)


class Site:
    data: List[DataNode]
    indices: List[IndexNode]
    documents: List[DocumentNode]
    resources: List[ResourceNode]
    static: List[StaticNode]
    generated: List[GeneratedNode]
    __nodes: Dict[pathlib.PurePosixPath, Node]
    __root = pathlib.PurePosixPath('/')
    __collections: Dict[str, Collection]

    def __init__(self):
        self.data = []
        self.indices = []
        self.documents = []
        self.resources = []
        self.static = []
        self.generated = []
        self.__nodes = {}
        self.__collections = {}

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
        """This creates links between parents/children.

        We have to do this in a separate step, as we merge static/resource
        nodes from themes etc."""
        for key, node in self.__nodes.items():
            parent_path = key.parent
            parent_node = self.__nodes.get(parent_path)
            # The parent_node != node check is required so the root node
            # doesn't get added to itself (by virtue of / being a parent of /)
            if parent_node and parent_node != node:
                parent_node.add_child(node)

    def create_collections(self, collections):
        for name, collection in collections.items():
            order_by = collection.get('order_by', [])
            self.__collections[name] = Collection(self, collection['filter'],
                                                  order_by)

    def get_next_in_collection(self, collection, node) -> Optional[Node]:
        next_node = self.__collections[collection].get_next(node)
        return next_node

    def get_previous_in_collection(self, collection, node) -> Optional[Node]:
        previous_node = self.__collections[collection].get_previous(node)
        return previous_node

    def get_node(self, path: pathlib.PurePosixPath) -> Optional[Node]:
        return self.__nodes.get(path)

    def select(self, query: str) -> List[Node]:
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
