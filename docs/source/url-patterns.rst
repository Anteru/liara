URL patterns
============

.. _url-patterns:

Liara uses a :py:class:`~liara.query.Query` in various places to match node paths. A query uses an "URL pattern", which, while looking similar to a file glob, matches the actual path structure instead of matching parts of the folder/file names. The syntax is as following:

* ``*`` matches anything but a subpath (i.e., ``/foo/*`` will match ``/foo/bar``, but not ``/foo/bar/baz``)
* ``**`` matches anything recursively (i.e. ``/foo/**`` will match any path starting with ``/foo/``)

Partial strings are not matched, i.e. ``/foo*`` or ``/f*o`` are invalid URL patterns. ``?`` is also not supported for URL patterns.

.. warning::

    The URL pattern syntax is not the same as the template path pattern syntax (see :doc:`templates`.) Template path patterns use string matching with no knowledge of path structures.