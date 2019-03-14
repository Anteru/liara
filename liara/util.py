import pathlib
import collections


def pairwise(iterable):
    """For a list ``s``, return pairs for consecutive entries. For example,
    a list ``s0``, ``s1``, etc. will produce ``(s0,s1), (s1,s2), ...`` and so
    on.

    See: https://docs.python.org/3/library/itertools.html#recipes."""
    import itertools
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def add_suffix(path: pathlib.Path, suffix):
    """Add a suffix to a path.

    This differs from ``with_suffix`` by adding a suffix without changing
    the extension, i.e. adding ``en`` to ``foo.baz`` will produce
    ``foo.en.baz``."""
    name = path.name
    name, sep, extension = name.rpartition('.')
    return path.with_name(name + '.' + suffix + '.' + extension)


def readtime(wordcount: int, words_per_minute=300):
    """Given a number of words, estimate the time it would take to read
    them.

    :return: The time in minutes if it's more than 1, otherwise 1."""
    return max(1, round(wordcount / 300))


def flatten_dictionary(d, sep='.', parent_key=None):
    """Flatten a nested dictionary. This uses the separator to combine keys
    together, so a dictionary access like ``['a']['b']`` with a separator
    ``'.'`` turns into ``'a.b'``."""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.Mapping):
            items.extend(flatten_dictionary(v, sep=sep,
                                            parent_key=new_key).items())
        else:
            items.append((new_key, v,))
    return dict(items)
