URL patterns
============

.. _url-patterns:

The :py:meth:`~liara.site.Site.select` method uses an "URL pattern" to match nodes by their path. URL patterns match the structure of a path instead of the individual components. They support two match patterns which work as following:

* ``*`` matches a path leaf: ``/foo/*`` will match ``/foo/bar``, but not ``/foo/bar/baz``, as ``/foo/bar/baz`` is not directly below ``/foo/``
* ``**`` matches anything recursively: ``/foo/**`` will match any path starting with ``/foo/``, for example ``/foo/bar/baz``

Partial strings are not matched, i.e. ``/foo*`` or ``/f*o`` are invalid URL patterns. ``?`` is also not supported for URL patterns.

.. warning::

    The URL pattern syntax is not the same as the template path pattern syntax (see :doc:`templates`.) Template path patterns use string matching with no knowledge of path structures.