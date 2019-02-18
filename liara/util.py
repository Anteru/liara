import pathlib


def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ...
    See: https://docs.python.org/3/library/itertools.html#recipes"""
    import itertools
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def add_suffix(path: pathlib.Path, suffix):
    name = path.name
    name, sep, extension = name.rpartition('.')
    return path.with_name(name + '.' + suffix + '.' + extension)
