from typing import Iterable, List, Iterator
from .nodes import Node
from .template import Page


class SelectionFilter:
    def match(self, node: Node) -> bool:
        pass


class MetadataFilter(SelectionFilter):
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


class TagFilter(SelectionFilter):
    def __init__(self, name):
        self.__name = name

    def match(self, node: Node) -> bool:
        tags = node.metadata.get('tags')
        if tags is not None:
            return self.__name in tags
        return False


class Sorter:
    def __init__(self):
        self._reverse = False

    def get_key(self, item):
        pass

    @property
    def reverse(self):
        return self._reverse


class TitleSorter(Sorter):
    def get_key(self, item: Page):
        return item.metadata.get('title').lower()


class DateSorter(Sorter):
    def __init__(self, reverse):
        self._reverse = reverse

    def get_key(self, item: Page):
        return item.metadata.get('date')


class TagSorter(Sorter):
    def __init__(self, tag: str):
        self.__tag = tag

    def get_key(self, item: Page):
        return item.metadata.get(self.__tag)


class Query(Iterable[Node]):
    __filters: List[SelectionFilter]
    __nodes: List[Node]
    __sorters: List[Sorter]
    __limit: int

    def __init__(self, nodes):
        self.__nodes = nodes
        self.__limit = -1
        self.__filters = []
        self.__sorters = []

    def limit(self, limit) -> 'Query':
        self.__limit = limit
        return self

    def with_metadata(self, name, value=None) -> 'Query':
        self.__filters.append(MetadataFilter(name, value))
        return self

    def with_tag(self, name) -> 'Query':
        self.__filters.append(TagFilter(name))
        return self

    def sorted_by_title(self) -> 'Query':
        self.__sorters.append(TitleSorter())
        return self

    def sorted_by_date(self, reverse=False) -> 'Query':
        self.__sorters.append(DateSorter(reverse))
        return self

    def sorted_by_tag(self, tag: str) -> 'Query':
        self.__sorters.append(TagSorter(tag))
        return self

    def __iter__(self) -> Iterator[Page]:
        result = self.__nodes
        for f in self.__filters:
            result = filter(lambda x: f.match(x), result)

        if self.__sorters:
            for s in self.__sorters:
                result = sorted(result, key=s.get_key, reverse=s.reverse)

        if self.__limit > 0:
            for i, e in enumerate(result):
                yield Page(e)
                if i > self.__limit:
                    break
        else:
            for e in result:
                yield Page(e)

    def __len__(self) -> int:
        i = 0
        it = iter(self)
        try:
            while True:
                next(it)
                i += 1
        except StopIteration:
            return i
