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
        """This creates links between parents/children.

        We have to do this in a separate step, as we merge static/resource
        nodes from themes etc."""
        for key, node in self.__nodes.items():
            parent_path = key.parent
            parent_node = self.__nodes.get(parent_path)
            if parent_node:
                parent_node.add_child(node)

    def get_node(self, path: pathlib.PurePosixPath) -> Optional[Node]:
        return self.__nodes.get(path)
