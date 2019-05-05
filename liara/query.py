from typing import Iterable, List, Iterator
from .nodes import Node
from .template import Page

import re


class SelectionFilter:
    """Base class for query selection filters."""
    def match(self, node: Node) -> bool:
        """Return ``True`` if the node should be kept, else ``False``."""
        pass


class MetadataFilter(SelectionFilter):
    """Filter items which contain a specific metadata field and optionally
    check if that field matches the provided value.
    """
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
    """Filter items by a specific tag, this expects a metadata field named
    ``tags`` to be present, and that field must support checks for containment
    using ``in``."""
    def __init__(self, name):
        self.__name = name

    def match(self, node: Node) -> bool:
        tags = node.metadata.get('tags')
        if tags is not None:
            return self.__name in tags
        return False


class ExcludeFilter(SelectionFilter):
    """Filter items by a provided pattern. The pattern is matched against the
    path. If it matches, the item will be ignored."""
    def __init__(self, pattern):
        self.__pattern = re.compile(pattern)

    def match(self, node: Node) -> bool:
        path = str(node.path)
        return self.__pattern.search(path) is None


class Sorter:
    """Base class for query sorters."""
    def __init__(self, reverse=False):
        self._reverse = reverse

    def get_key(self, item):
        """Return the key to be used for sorting."""
        pass

    @property
    def reverse(self):
        """Returns ``True`` if the sort order should be reversed."""
        return self._reverse


class MetadataSorter(Sorter):
    """Sort nodes by metadata."""
    def __init__(self, item: str, reverse=False, case_sensitive=False):
        super().__init__(reverse)
        self.__item = item
        self.__case_sensitive = case_sensitive

    def get_key(self, item: Page):
        key = item.metadata.get(self.__item)
        if isinstance(key, str) and self.__case_sensitive is False:
            return key.lower()
        return key


class Query(Iterable[Node]):
    """A query modifies a list of nodes, by sorting and filtering entries.
    """

    __filters: List[SelectionFilter]
    __nodes: List[Node]
    __sorters: List[Sorter]
    __limit: int
    __reversed: bool
    __result: List[Page]

    def __init__(self, nodes):
        self.__nodes = nodes
        self.__limit = -1
        self.__filters = []
        self.__sorters = []
        self.__reversed = False
        self.__result = None

    def limit(self, limit) -> 'Query':
        """Limit this query to return at most ``limit`` results."""
        self.__limit = limit
        return self

    def with_metadata(self, name, value=None) -> 'Query':
        """Limit this query to only include nodes which contain the specific
        metadata field.

        :param value: If ``value`` is provided, the field must exist and match
                      the provided value.
        """
        self.__filters.append(MetadataFilter(name, value))
        return self

    def with_tag(self, name) -> 'Query':
        """Limit this query to only include nodes with a metadata field named
        ``tags`` which contains the specified tag name.
        """
        self.__filters.append(TagFilter(name))
        return self

    def exclude(self, pattern) -> 'Query':
        """Exclude nodes matching the provided regex pattern. The pattern will
        be applied to the full path."""
        self.__filters.append(ExcludeFilter(pattern))
        return self

    def sorted_by_title(self, *, reverse=False) -> 'Query':
        """Sort the entries in this query by the metadata field ``title``."""
        return self.sorted_by_metadata('title', reverse=reverse)

    def sorted_by_date(self, *, reverse=False) -> 'Query':
        """Sort the entries in this query by the metadata field ``date``."""
        return self.sorted_by_metadata('date', reverse=reverse)

    def sorted_by_metadata(self, tag: str, *,
                           reverse=False, case_sensitive=False) -> 'Query':
        """Sort the entries in this query by the specified metadata field."""
        self.__sorters.append(MetadataSorter(tag, reverse, case_sensitive))
        return self

    def reversed(self) -> 'Query':
        """Return the results of this query in reversed order."""
        self.__reversed = True
        return self

    def __execute(self):
        if self.__result is not None:
            return

        self.__result = []
        result = self.__nodes
        for f in self.__filters:
            result = filter(lambda x: f.match(x), result)

        if self.__sorters:
            for s in self.__sorters:
                result = sorted(result, key=s.get_key, reverse=s.reverse)

        if self.__reversed:
            result = reversed(result)

        if self.__limit > 0:
            for i, e in enumerate(result):
                if i >= self.__limit:
                    break
                self.__result.append(Page(e))
        else:
            for e in result:
                self.__result.append(Page(e))

    def __iter__(self) -> Iterator[Page]:
        self.__execute()
        return iter(self.__result)

    def __len__(self) -> int:
        self.__execute()
        return len(self.__result)
