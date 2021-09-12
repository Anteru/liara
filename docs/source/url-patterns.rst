URL patterns
============

.. _url-patterns:

In various places Liara allows matching content by URL pattern. This is very similar to matching files using a glob pattern. The syntax is as following:

* ``*`` matches anything but a subpath (i.e., ``/foo/*`` will match ``/foo/bar``, but not ``/foo/bar/baz``)
* ``**`` matches anything recursively (i.e. ``/foo/**`` will match any path starting with ``/foo/``)

Partial strings are not matched, i.e. ``/foo*`` or ``/f*o`` are invalid URL patterns. ``?`` is also not supported for URL patterns.

.. warning::

    The URL pattern syntax is not the same as the template path pattern syntax (see :doc:`templates`.) URL patterns are used in conjunction with a :py:class:`~liara.query.Query` which allows for fine-grained, programmatic filtering, while template patterns are plain strings.