import pathlib
import collections.abc
import datetime
import tzlocal
from typing import List, Optional
import os
import fnmatch


def pairwise(iterable):
    """For a list ``s``, return pairs for consecutive entries. For example,
    a list ``s0``, ``s1``, etc. will produce ``(s0,s1), (s1,s2), ...`` and so
    on.

    See: https://docs.python.org/3/library/itertools.html#recipes."""
    import itertools
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def add_suffix(path: pathlib.PurePosixPath, suffix):
    """Add a suffix to a path.

    This differs from ``with_suffix`` by adding a suffix without changing
    the extension, i.e. adding ``en`` to ``foo.baz`` will produce
    ``foo.en.baz``."""
    name = path.name
    name, _, extension = name.rpartition('.')
    return path.with_name(name + '.' + suffix + '.' + extension)


def readtime(wordcount: int, words_per_minute=300):
    """Given a number of words, estimate the time it would take to read
    them.

    :return: The time in minutes if it's more than 1, otherwise 1."""
    return max(1, round(wordcount / 300))


def flatten_dictionary(d, sep='.', parent_key=None,
                       *, ignore_keys: Optional[set] = None):
    """Flatten a nested dictionary. This uses the separator to combine keys
    together, so a dictionary access like ``['a']['b']`` with a separator
    ``'.'`` turns into ``'a.b'``.

    If ``ignore_keys`` is set, it must be a list of fully flattened key names
    at which the flattening should stop. For instance, if a dictionary
    ``{'a': {'b': {'c': 1}}}`` is provided, and ``ignore_keys`` is ``{'a.b'}``,
    then ``a.b`` will not get flattened further, so ``a.b`` will contain a
    dictionary with ``{'c': 1}``.
    """
    items = []
    ignore_keys = ignore_keys if ignore_keys else set()

    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.abc.Mapping) \
           and new_key not in ignore_keys:
            items.extend(flatten_dictionary(v, sep=sep,
                                            parent_key=new_key,
                                            ignore_keys=ignore_keys).items())
        else:
            items.append((new_key, v,))
    return dict(items)


def create_slug(s: str) -> str:
    """Convert a plain string into a slug.

    A slug is suitable for use as a URL. For instance, passing ``A new world``
    to this function will return ``a-new-world``.
    """
    import slugify
    return slugify.slugify(s)


__TZ = tzlocal.get_localzone()
__override_now = None


def set_local_now(dt: datetime.datetime):
    """
    Override "now" to allow previewing the page at a different point in time.
    """
    global __override_now
    __override_now = dt.astimezone(__TZ)


def local_now() -> datetime.datetime:
    """Get the current date/time in the local time zone.

    This is equivalent to ``datetime.datetime.now()``, except it returns a
    timestamp which has ``tzinfo`` set to the local timezone.

    This can be overridden using ``set_local_now`` to build the page at a
    different point in time.
    """
    if __override_now:
        return __override_now
    return datetime.datetime.now(tz=__TZ)


class FilesystemWalker:
    def __init__(self, ignore_files: Optional[List[str]] = None):
        self.__ignore_files = ignore_files if ignore_files else []

    def walk(self, path: pathlib.Path):
        """Walk a directory recursively.

        This is quite similar to ``os.walk``, but with two major differences:

        * Files matching the ``ignore_files`` pattern are ignored.
        * The ``dirnames`` part of the tuple is omitted
        """
        for dirpath, _, filenames in os.walk(path):
            files_to_ignore = set()
            for pattern in self.__ignore_files:
                for filename in fnmatch.filter(filenames, pattern):
                    files_to_ignore.add(filename)

            filenames = [filename for filename in filenames
                         if filename not in files_to_ignore]

            yield dirpath, filenames
